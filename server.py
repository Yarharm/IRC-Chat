import socket
import select
import sys
import logging
import commands
import constants
import errors
from util_server import ServerUtil

"""
Description:

Client object encapsulation

"""
class Client:
    def __init__(self, addr):
        self.addr = addr
        self.nickname = ''
        self.username = ''
    
    # Set nickname and username
    def register(self, property_value, property_type):
        if property_type == commands.NICKNAME:
            self.nickname = property_value
        if property_type == commands.USERNAME:
            self.username = property_value
    
    def registration_status(self):
        return self.nickname and self.username
    
    def get_nickname(self):
        return self.nickname

    def get_username(self):
        return self.username

    def get_addr(self):
        return self.addr

"""
Description:

IRC Server

"""
class Server:
    def __init__(self, args):
        self.host = '127.0.0.1'
        self.port = self.__fetch_port(args)
        self.socket = None
        self.input_sources = list()
        self.output_sources = list()
        self.clients = dict() # socket -> Client
        self.nicknames = set()
        self.buffer = dict() # socket -> message str
        self.logger = None
    
    def __fetch_port(self, args):
        port = 6667
        if len(args) != 0 and (len(args) != 2 or args[0] != '--port' or not args[1].isnumeric()):
            print('Invalid argument list. Usage: server.py [--port PORT]')
            sys.exit()
        if len(args) == 2:
            port = int(args[1])
        return port

    def __init_logger(self):
        logging.basicConfig(filename='log-server.log', filemode='w+', level=logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.info('Logger is online')

    def __listen(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        self.logger.info(f'Server is listening on port {self.port}')

    def __prepare_select(self):
        self.input_sources.append(self.socket)
        self.logger.info(f'Server is ready to accept messages from {len(self.input_sources)} sources')

    def __get_client_addr(self, client_socket):
        return self.clients[client_socket].get_addr() if client_socket in self.clients else 'Address no longer available'

    def __get_client_nickname(self, client_socket):
        return self.clients[client_socket].get_nickname() if client_socket in self.clients else ''
    
    def __get_client_username(self, client_socket):
        return self.clients[client_socket].get_username() if client_socket in self.clients else ''
    
    def __get_client_registration_status(self, client_socket):
        return self.clients[client_socket].registration_status() if client_socket in self.clients else False

    def __remove_nickname(self, client_socket):
        self.nicknames.discard(self.__get_client_nickname(client_socket))

    def __remove_dead_connections(self):
        for client_socket in self.input_sources:
            if client_socket.fileno() == -1:
                self.__close_client_connection(client_socket)
    
    def __build_response(self, client_socket, response_message):
        nickname = self.__get_client_nickname(client_socket)
        response = f'{response_message}{constants.COMMAND_END_DELIM}'
        response = f'{constants.COMMAND_PREFIX_DELIM}{nickname} {response}' if nickname else response
        response = response.encode(constants.COMMAND_ENCODING)
        return response

    def __accept_client_connection(self):
        client_socket, client_addr = self.socket.accept()
        client_socket.setblocking(0)
        self.input_sources.append(client_socket)
        self.output_sources.append(client_socket) # Remove IRC
        self.clients[client_socket] = Client(client_addr)
        self.buffer[client_socket] = ""
        self.logger.info(f'Accepted new connection with address {self.__get_client_addr(client_socket)}')

    def __close_client_connection(self, client_socket):
        addr = self.__get_client_addr(client_socket)
        self.input_sources.remove(client_socket)
        self.output_sources.remove(client_socket)
        self.__remove_nickname(client_socket)
        self.clients.pop(client_socket, 'OK')
        self.buffer.pop(client_socket, 'OK')
        client_socket.close()
        self.logger.info(f'Closed client connection with address {addr}')
    
    # Register message in the buffer
    def __register_request(self, client_socket, request):
        self.buffer[client_socket] += request
        self.logger.info(f'Received request {repr(request)} from client with address {self.__get_client_addr(client_socket)}')
    
    # Handle broadcast request
    def __handle_broadcast(self, client_socket, request):
        response_message = ServerUtil.get_broadcast_message(request)
        client_nickname = self.__get_client_nickname(client_socket)
        client_username = self.__get_client_username(client_socket)
        
        # No registered Nickname
        if client_nickname not in self.nicknames or not client_nickname:
            self.logger.warning(f'Client broadcast denided, no such NICK. Responding with "401 ERR_NOSUCHNICK"')
            response_message = f'{errors.ERR_NOSUCHNICK_CODE} {client_nickname} {errors.ERR_NOSUCHNICK_MESSAGE}'
        # No registered Username
        elif not client_username:
            self.logger.warning(f'Client broadcast denided, no such USER. Responding with "404 ERR_CANNOTSENDTOCHAN"')
            response_message = f'{errors.ERR_CANNOTSENDTOCHAN_CODE} {constants.GLOBAL_CHANNEL} {errors.ERR_CANNOTSENDTOCHAN_MESSAGE}'
        # Execute broadcast
        else:
            response = self.__build_response(client_socket, response_message)
            for channel_member in self.output_sources:
                if channel_member != client_socket and self.__get_client_registration_status(channel_member):
                    self.logger.info(f'Sending broadcast {repr(response)} to the client address {self.__get_client_addr(channel_member)}')
                    channel_member.sendall(response)
        response = self.__build_response(client_socket, response_message)
        self.logger.info(f'Sending broadcast {repr(response)} to the original sender {self.__get_client_addr(client_socket)}')
        client_socket.sendall(response)
        
    # Handle nickname request
    def __handle_nickname(self, client_socket, request):
        nickname = ServerUtil.get_nick_nickname(request)
        response_message = ''
        # No nickname provided
        if not nickname:
            self.logger.warning('Nickname parameter was not found. Responding with "431 ERR_NONICKNAMEGIVEN"')
            response_message = f'{errors.ERR_NONICKNAMEGIVEN_CODE} {errors.ERR_NONICKNAMEGIVEN_MESSAGE}'
        # Nickname length is beyond 9 chars
        elif len(nickname) > 9:
            self.logger.warning(f'Nickname "{nickname}"" is too long. Responding with "432 ERR_ERRONEUSNICKNAME"')
            response_message = f'{errors.ERR_ERRONEUSNICKNAME_CODE} {nickname} {errors.ERR_ERRONEUSNICKNAME_MESSAGE}'
        # User is trying to change nickname to already taken one
        elif nickname in self.nicknames and self.__get_client_nickname(client_socket):
            self.logger.warning(f'Cannot change! Nickname "{nickname}" is already in use. Responding with "433 ERR_NICKNAMEINUSE"')
            response_message = f'{errors.ERR_NICKNAMEINUSE_CODE} {nickname} {errors.ERR_NICKNAMEINUSE_MESSAGE}'
        # User is trying to register nickanme to already taken one
        elif nickname in self.nicknames:
            self.logger.warning(f'Cannot register! Nickname "{nickname}" collision. Responding with "436 ERR_NICKCOLLISION"')
            response_message = f'{errors.ERR_NICKCOLLISION_CODE} {nickname} {errors.ERR_NICKCOLLISION_MESSAGE}'
        # Register nickname
        else:
            old_nickname = self.__get_client_nickname(client_socket)
            # Client changing nickname
            if old_nickname:
                self.__remove_nickname(client_socket)
                self.logger.info(f'Successfully changed "{old_nickname}" nickname to "{nickname}" for the client {self.__get_client_addr(client_socket)}')
            # Client registering fresh nickname
            else:
                self.logger.info(f'Successfully registered nickname "{nickname}" for the client {self.__get_client_addr(client_socket)}')
            self.nicknames.add(nickname)
            self.clients[client_socket].register(nickname, commands.NICKNAME)
            return
        response = self.__build_response(client_socket, response_message)
        self.logger.info(f'Sending NICK command result to the client {repr(response)}')
        client_socket.sendall(response)

    # Handle username request
    def __handle_username(self, client_socket, request):
        response_message = ''
        # Not valid paramters count
        if not ServerUtil.user_valid_params(request):
            self.logger.warning(f'USER request {repr(request)} does not have enough paramteres. Responsing with "461 ERR_NEEDMOREPARAMS"')
            response_message = f'{errors.ERR_NEEDMOREPARAMS_CODE} {commands.USERNAME} {errors.ERR_NEEDMOREPARAMS_MESSAGE}'
        # Client tries to repeat username registration
        elif self.__get_client_username(client_socket):
            self.logger.warning(f'USER request already registered. Responding with "462 ERR_ALREADYREGISTRED"')
            response_message = f'{errors.ERR_ALREADYREGISTRED_CODE} {errors.ERR_ALREADYREGISTRED_MESSAGE}'
        # Register username. No response sent to the client
        else:
            username = ServerUtil.get_user_username(request)
            self.clients[client_socket].register(username, commands.USERNAME)
            self.logger.info(f'Successfully registered username "{username}" for the client {self.__get_client_addr(client_socket)}')
            return
        response = self.__build_response(client_socket, response_message)
        self.logger.info(f'Sending USER command result to the client {repr(response)}')
        client_socket.sendall(response) 

    # Process request in buffer
    def __process_request(self, client_socket, buffered_request):
        if constants.COMMAND_END_DELIM not in buffered_request:
            self.logger.info(f'Request "{buffered_request}" does not contain CR-LF termination. Postponing processing!')
            return

        # Get request from buffer
        request, request_delim = ServerUtil.get_request_from_buffer(buffered_request)
        self.buffer[client_socket] = buffered_request[request_delim:] # update buffer

        # Request processing
        self.logger.info(f'Processing request {repr(request)} from client with address {self.__get_client_addr(client_socket)}')
        command_type = ServerUtil.get_command_type(request)
        if command_type == commands.NICKNAME:
            self.__handle_nickname(client_socket, request)
        elif command_type == commands.USERNAME:
            self.__handle_username(client_socket, request)
        else:
            self.__handle_broadcast(client_socket, request)
        

    # Main event loop
    def run(self):
        while True:
            read_sockets, write_sockets, err_sockets = select.select(self.input_sources, self.output_sources, self.input_sources)

            # Handle read sockets
            for read_socket in read_sockets:
                if read_socket == self.socket:
                    self.__accept_client_connection()
                else:
                    request = read_socket.recv(4096).decode(constants.COMMAND_ENCODING)
                    if request:
                        self.__register_request(read_socket, request)
                    else:
                        self.logger.warning('Client disconnected. Closing connection from __read_sockets__')
                        self.__close_client_connection(read_socket)
            
            # Handle write sockets
            for write_socket in write_sockets:
                buffered_request = self.buffer[write_socket] if write_socket in self.buffer else ''
                if buffered_request:
                    self.__process_request(write_socket, buffered_request)
            
            # Handle error sockets
            for err_socket in err_sockets:
                self.logger.warning('Closing connection from __err_sockets__')
                self.__close_client_connection(err_socket)
            
    # Prepare server
    def coldstart(self):
        self.__init_logger()
        self.__listen()
        self.__prepare_select()
    
    # Close resources
    def shutdown(self, e):
        self.logger.info(f'Shutting down with error name {type(e).__name__} and message {e}')
        self.__remove_dead_connections()
        if self.socket is not None:
            self.socket.close()

if __name__ == "__main__":
    server = Server(sys.argv[1:])
    try:
        server.coldstart()
        server.run()
    except Exception as e:
        server.shutdown(e)
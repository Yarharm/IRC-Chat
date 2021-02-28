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
    # Return True if user is registered; False otherwise
    def register(self, property_value, property_type):
        if property_type == commands.NICKNAME:
            self.nickname = property_value
        if property_type == commands.USERNAME:
            self.username = property_value
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
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 6667
        self.socket = None
        self.input_sources = list()
        self.output_sources = list()
        self.clients = dict() # socket -> Client
        self.nicknames = set()
        self.buffer = dict() # socket -> message str
        self.logger = None

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

    def __remove_nickname(self, client_socket):
        self.nicknames.discard(self.__get_client_nickname(client_socket))

    def __remove_dead_connections(self):
        for client_socket in self.input_sources:
            if client_socket.fileno() == -1:
                self.__close_client_connection(client_socket)

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
        response = ServerUtil.build_response(response_message)
        for channel_member in self.output_sources:
            self.logger.info(f'Sending response {repr(response)} to the client address {self.__get_client_addr(channel_member)}')
            channel_member.sendall(response)
        
    # Handle nickname request
    def __handle_nickname(self, client_socket, request):
        nickname = ServerUtil.get_nickname_message(request)
        response_message = ''
        if not nickname:
            self.logger.warning('Nickname parameter was not found. Responding with "431 ERR_NONICKNAMEGIVEN"')
            response_message = f'{errors.ERR_NONICKNAMEGIVEN_CODE} {errors.ERR_NONICKNAMEGIVEN_MESSAGE}'
        elif len(nickname) > 9:
            self.logger.warning(f'Nickname "{nickname}"" is too long. Responding with "432 ERR_ERRONEUSNICKNAME"')
            response_message = f'{errors.ERR_ERRONEUSNICKNAME_CODE} {nickname} {errors.ERR_ERRONEUSNICKNAME_MESSAGE}'
        elif nickname in self.nicknames and self.__get_client_nickname(client_socket):
            self.logger.warning(f'Cannot change! Nickname "{nickname}" is already in use. Responding with "433 ERR_NICKNAMEINUSE"')
            response_message = f'{errors.ERR_NICKNAMEINUSE_CODE} {nickname} {errors.ERR_NICKNAMEINUSE_MESSAGE}'
        elif nickname in self.nicknames:
            self.logger.warning(f'Cannot register! Nickname "{nickname}" collision. Responding with "436 ERR_NICKCOLLISION"')
            response_message = f'{errors.ERR_NICKCOLLISION_CODE} {nickname} {errors.ERR_NICKCOLLISION_MESSAGE}'
        else:
            old_nickname = self.__get_client_nickname(client_socket)
            # Client already had nickname
            if old_nickname:
                self.__remove_nickname(client_socket)
                self.logger.info(f'Successfully changed "{old_nickname}" nickname to "{nickname}" for the client {self.__get_client_addr(client_socket)}')
                response_message = f'{old_nickname} {constants.COMMAND_NICK_CHANGE_SUCCESS} "{nickname}".'
            # New client nickname registration
            else:
                self.logger.info(f'Successfuly registered nickname "{nickname}" for the client {self.__get_client_addr(client_socket)}')
                response_message = f'{constants.COMMAND_NICK_REGISTER_SUCCESS} "{nickname}".'

            self.nicknames.add(nickname)
            _registered = self.clients[client_socket].register(nickname, commands.NICKNAME)
            # if registered:
            #     self.output_sources.append(client_socket) # FIX IT: ADD TO OUTPUT SOURCES ONLY ONCE
        response = ServerUtil.build_response(response_message)
        self.logger.info(f'Sending NICK command result to the client {repr(response)}')
        client_socket.sendall(response)

    # Generate message response 
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
        # FIX HERE: IF NICKNAME IS ATTACHED VERIFY THAT IT IS ACTUALLY REGISTERED WITH THE SERVER
        if command_type == commands.BROADCAST:
            self.__handle_broadcast(client_socket, request)
        elif command_type == commands.NICKNAME:
            self.__handle_nickname(client_socket, request)
        

    # Main event loop
    def run(self):
        while True:
            try:
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
                # Bug is connection is closed in __read_sockets__ then buffer does not exists event if message is there
                for write_socket in write_sockets:
                    buffered_request = self.buffer[write_socket] if write_socket in self.buffer else ''
                    if buffered_request:
                        self.__process_request(write_socket, buffered_request)
            
                # Handle error sockets
                for err_socket in err_sockets:
                    self.logger.warning('Closing connection from __err_sockets__')
                    self.__close_client_connection(err_socket)

            except socket.error as e:
                self.logger.warning(f'Client exited abruptly with error name {type(e).__name__} and message {e}')
                self.__remove_dead_connections()
                # self.logger.info(f'Run event 1 {type(e).__name__}')
                # self.logger.info(f'Run event 2 {e.__class__.__name__}')
                # self.logger.info(f'Run event 3 {e.__class__.__qualname__}'
            
    # Prepare server
    def coldstart(self):
        self.__init_logger()
        self.__listen()
        self.__prepare_select()
    
    # Close resources
    def shutdown(self, e):
        self.logger.info(f'Shutting down with error name {type(e).__name__} and message {e}')
        for client_socket in self.input_sources:
                    if client_socket.fileno() == -1:
                        self.__close_client_connection(client_socket)
        if self.socket is not None:
            self.socket.close()

if __name__ == "__main__":
    # Parse your command line arguments here
    # main(sys.argv[1:])
    server = Server()
    try:
        server.coldstart()
        server.run()
    except Exception as e:
        server.shutdown(e)
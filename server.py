import socket
import select
import sys
import logging
import commands
import constants

class Client:
    def __init__(self, addr):
        self.addr = addr

    def get_addr(self):
        return self.addr

class Server:
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 6667
        self.socket = None
        self.input_sources = list()
        self.output_sources = list()
        self.clients = {} # socket -> Client
        self.buffer = {} # socket -> message str
        self.logger = None
        self.encoding = 'utf-8'

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
        self.clients.pop(client_socket, 'OK')
        self.buffer.pop(client_socket, 'OK')
        client_socket.close()
        self.logger.info(f'Closed client connection with address {addr}')
    
    # Register message in the buffer
    def __register_request(self, client_socket, request):
        self.buffer[client_socket] += request
        self.logger.info(f'Received request {repr(request)} from client with address {self.__get_client_addr(client_socket)}')

    # Generate message response 
    def __process_request(self, client_socket, buffered_request):
        if constants.MESSAGE_END_DELIM not in buffered_request:
            self.logger.info(f'Request "{buffered_request}" does not contain CR-LF termination. Postponing processing!')
            return

        # Get request from buffer
        request_delim = buffered_request.index(constants.MESSAGE_END_DELIM)
        request = buffered_request[:request_delim]
        self.buffer[client_socket] = buffered_request[request_delim + len(constants.MESSAGE_END_DELIM):] # update buffer

        # Request processing
        self.logger.info(f'Processing request "{request}" from client with address {self.__get_client_addr(client_socket)}')
        request_split = request.split(' ')
        command_type = request_split[1] if constants.PREFIX_DELIM in request_split[0] else request_split[0]
        nick_shift = 1 if constants.PREFIX_DELIM in request_split[0] else 0

        response = ""
        if command_type == commands.BROADCAST:
            _channel, msg = request_split[1 + nick_shift], request_split[2 + nick_shift]
            response = f'{msg[1:]}{constants.MESSAGE_END_DELIM}'
            for channel_member in self.output_sources:
                self.logger.info(f'Sending response {repr(response)} to the client address {self.__get_client_addr(channel_member)}')
                client_socket.sendall(response.encode(self.encoding))
        

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
                        request = read_socket.recv(4096).decode(self.encoding)
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
            except KeyError as e:
                self.logger.warning(f'Server has messed up dictionary keys. Error name {type(e).__name__} and message {e}')
            
    # Prepare server
    def coldstart(self):
        self.__init_logger()
        self.__listen()
        self.__prepare_select()
    
    # Close resources
    def shutdown(self, e):
        self.logger.info(f'Shutting down with err: {e}')
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
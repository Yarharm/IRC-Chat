import socket
import select
import sys
import logging

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
        self.logger.info(f'Attempting to close connection with {addr}')
        self.input_sources.remove(client_socket)
        self.output_sources.remove(client_socket)
        self.clients.pop(client_socket, 'OK')
        self.buffer.pop(client_socket, 'OK')
        client_socket.close()
        self.logger.info(f'Closed client connection with address {addr}')
    
    def __register_message(self, client_socket, msg):
        self.buffer[client_socket] += msg
        self.logger.info(f'Received message "{msg}" from client with address {self.__get_client_addr(client_socket)}')
    
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
                        msg = read_socket.recv(4096).decode('utf-8')
                        if msg:
                            self.__register_message(read_socket, msg)
                        else:
                            self.logger.warn('Bad boy 1')
                            self.__close_client_connection(read_socket)
            
                # Handle write sockets
                # Bug is connection is closed in __read_sockets__ then buffer does not exists event if message is there
                for write_socket in write_sockets:
                    msg = self.buffer[write_socket] if write_socket in self.buffer else ''
                    if msg:
                        # Broadcast
                        for client_socket in self.output_sources:
                            self.logger.info(f'Sending message "{msg}" to the client address {self.__get_client_addr(client_socket)}')
                            client_socket.sendall(msg.encode('utf-8'))
                        self.buffer[write_socket] = ''
            
                # Handle error sockets
                for err_socket in err_sockets:
                    self.logger.warn('Some socket is broken in err_sockets')
                    self.__close_client_connection(err_socket)

            except socket.error as e:
                self.logger.warn(f'Client exited abruptly with error name {type(e).__name__} and message {e}')
                self.__remove_dead_connections()
                # self.logger.info(f'Run event 1 {type(e).__name__}')
                # self.logger.info(f'Run event 2 {e.__class__.__name__}')
                # self.logger.info(f'Run event 3 {e.__class__.__qualname__}'
            except KeyError as e:
                self.logger.warn(f'Server has messed dictionary keys. Error name {type(e).__name__} and message {e}')
            
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
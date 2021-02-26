import socket
import select
import threading
import sys
import logging

class Client:
    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 6667
        self.socket = None
        self.input_sources = list()
        self.logger = None
        
    def __init_logger(self):
        logging.basicConfig(filename='log-client.log', filemode='w+', level=logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.info('Logger is online')
    
    def __connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.setblocking(0)
        self.logger.info(f'Connected to the {self.host}:{self.port}')
    
    def __prepare_select(self):
        self.input_sources.append(self.socket)
        self.logger.info(f'Client ready to receive messages from {len(self.input_sources)} source')
    
    def coldstart(self):
        self.__init_logger()
        self.__connect()
        self.__prepare_select()

    def listen(self):
        self.logger.info('Listening in a thread')
        while True:
            read_sockets, _write_sockets, _err_sockets = select.select(self.input_sources, [], [])
            for read_socket in read_sockets:
                if read_socket == self.socket:
                    data = read_socket.recv(4096).decode('utf-8')
                    if not data:
                        self.logger.info('Server is dead. Shutting down...')
                        raise Exception
                    self.logger.info(f'Received data from the server: {data}')
                    sys.stdout.write(data)
                    sys.stdout.write('\n[]: ')
                    sys.stdout.flush()
                    
    def run(self):
        self.logger.info('Ready to accept input')
        while True:
            message = input('\n[]: ')
            # message = sys.stdin.readline()
            self.logger.info(f'Sending message to the server: {message}')
            self.socket.sendall(message.rstrip('\n').encode('utf-8'))
            #sys.stdout.write('\n[]: ')
            #sys.stdout.flush()
        
    def shutdown(self, e):
        self.logger.info(f'Shutting down client with err: {e}')
        if self.socket is not None:
            self.socket.close()

if __name__ == "__main__":
    # Parse your command line arguments here
    # main(sys.argv[1:])
    client = Client()
    try:
        client.coldstart()
        threading.Thread(target=client.listen, args=(), daemon=True).start()
        client.run()
    except Exception as e:
        client.shutdown(e)
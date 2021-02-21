# Echo server program
import sys
import socket
import commands
from message_manager import MessageManager

HOST = '127.0.0.1'
client_dict = {}
msg_manager = MessageManager()

class Client:
    def __init__(self):
        self.nickname = None
        self.username = None
        self.registered = False
    
    def set_nickname(self, nick):
        self.nickname = nick
        self.registered = True if self.username is not None else False
    
    def set_username(self, username):
        self.username = username
        self.registered = True if self.nickname is not None else False

def process_message(conn, msg):
    command, message = msg_manager.parse_message(msg)
    if command == commands.NICKNAME:
        client_dict[conn].set_nickname(message)
        print(f'Set new nickname {message}')
    elif command == commands.USERNAME:
        client_dict[conn].set_username(message)
        print(f'Set new username {message}')
    return message

def main(args):
    port = fetch_port_info(args)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, port))
        s.listen()
        print(f'Server is listening on port {port}')
        while True:
            conn, addr = s.accept()
            print(f'Accepted new connection {addr}')
            client_dict[conn] = Client()
            with conn:
                while True:
                    msg = conn.recv(4096)
                    print(f'Received message {msg}')
                    if not msg: 
                        break
                    data = process_message(conn, msg)
                    print(f'Message data is {data}')
            client_dict.pop(conn)
    
def fetch_port_info(args):
    port = 6667
    if(len(args) != 0 and (len(args) != 2 or args[0] != '--port' or not args[1].isnumeric())):
        print('Invalid arguments list. Usage: server.py [--port PORT]')
        sys.exit()
    if(len(args) == 2):
        port = int(args[1])
    return port

if __name__ == "__main__":
    # Parse your command line arguments here
    main(sys.argv[1:])
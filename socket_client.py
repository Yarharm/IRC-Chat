import socket
import commands
from message_manager import MessageManager

class SocketClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.nickname = None
        self.username = None
        self.socket = None
        self.msg_manager = MessageManager()

    def __sendall(self, msg, command):
        send_packet = self.msg_manager.build_message(msg, command)
        print(f'SENDING {send_packet}')
        self.socket.sendall(send_packet)

    def send_message(self, msg):
        data = 'No connection established. Provide username and nickname'
        if self.nickname is not None and self.username is not None:
            self.__sendall(msg, commands.BROADCAST)
            data = msg
        return data

    def register_nickname(self, nick):
        print(f'Receoved nickname {nick}')
        if len(nick) > 9:
            return 'Nickname is too long (Max 9 chars)'
        self.nickname = nick
        self.__sendall(nick, commands.NICKNAME)
        return f'Successfully registered nickname {self.nickname}'

    def register_username(self, username):
        print(f'Receoved username {username}')
        self.username = username
        self.__sendall(username, commands.USERNAME)
        return f'Successfully registered username {self.username}'

    def init_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
    
    def close_connection(self):
        self.socket.close()
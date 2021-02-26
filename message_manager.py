import commands 

ENCODING = 'utf-8'
GLOBAL_CHANNEL = '#global'

class MessageManager:
    def build_message(self, msg, command):
        packet = 'test_packet'
        if command == commands.NICKNAME:
            packet = f'{commands.NICKNAME} {msg}'
        elif command == commands.USERNAME:
            packet = f'{commands.USERNAME} {msg}'
        else:
            packet = f'{commands.BROADCAST} {GLOBAL_CHANNEL} {msg}'
        return packet.encode(ENCODING)

    def parse_message(self, msg):
        msg_split = msg.decode(ENCODING).split(' ')
        if msg_split[0] == commands.NICKNAME:
            return msg_split[0], msg_split[1]
        elif msg_split[0] == commands.USERNAME:
            return msg_split[0], msg_split[1]
        else:
            return msg_split[0], msg_split[2]

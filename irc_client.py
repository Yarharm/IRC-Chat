#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2021
#
# Distributed under terms of the MIT license.

"""
Description:

"""
import asyncio
import logging
import socket
import select
import threading
import queue
import patterns
import view
import sys
import commands
import constants

logging.basicConfig(filename='log-client.log', filemode='w+', level=logging.DEBUG)
logger = logging.getLogger()

class RequestBuilder:
    def build(self, msg, request_type, prefix=''):
        request = ""

        if request_type == commands.NICKNAME:
            nickname = msg[msg.index(constants.UI_NICK) + len(constants.UI_NICK):].strip()
            request = f'{commands.NICKNAME} {nickname}'
            request = f'{constants.COMMAND_PREFIX_DELIM}{prefix} {request}' if prefix else request
        elif request_type == commands.USERNAME:
            username = msg[msg.index(constants.UI_USER) + len(constants.UI_USER):].strip()
            hostname = 'hostname'
            servername = 'servername'
            request = f'{commands.USERNAME} {username} {hostname} {servername} {constants.COMMAND_REALNAME_DELIM}{username}'
        else:
            request = f'{commands.BROADCAST} {constants.GLOBAL_CHANNEL} {constants.COMMAND_MESSAGE_DELIM}{msg}'
            request = f'{constants.COMMAND_PREFIX_DELIM}{prefix} {request}' if prefix else request

        request += constants.COMMAND_END_DELIM
        logger.info(f'RequestBuilder prepared request {repr(request)}')
        return request.encode(constants.COMMAND_ENCODING)

class IRCClient(patterns.Subscriber):
    def __init__(self, host, port):
        super().__init__()
        self.nick = ''
        self._run = True
        self.host = host
        self.port = port
        self.socket = None
        self.request_builder = RequestBuilder()
        self.buffer = ''

    def set_view(self, view):
        self.view = view
    
    def add_msg(self, msg):
        self.view.add_msg(self.nick, msg)

    def init_tcp_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.setblocking(0)

    def update(self, msg):
        if not isinstance(msg, str):
            raise TypeError(f"Update argument needs to be a string")
        elif not len(msg):
            return
        logger.info(f"IRCClient.update -> msg: {msg}")
        self.process_input(msg)

    def process_input(self, msg):
        request = ""
        if msg.lower().startswith(constants.UI_QUIT):
            raise KeyboardInterrupt
        elif msg.lower().startswith(constants.UI_NICK):
            request = self.request_builder.build(msg, commands.NICKNAME, self.nick)
        elif msg.lower().startswith(constants.UI_USER):
            request = self.request_builder.build(msg, commands.USERNAME)
        else:
            request = self.request_builder.build(msg, commands.BROADCAST, self.nick)
        
        logger.info(f'Sending request {repr(request)}')
        self.socket.sendall(request)
    
    def __process_server_message(self, server_message):
        # Process optional prefix
        prefix_start = server_message.find(constants.COMMAND_PREFIX_DELIM)
        prefix_end = server_message.index(' ')
        prefix = server_message[prefix_start + 1: prefix_end] if prefix_start != -1 else ''
        self.nick = prefix
        # Process message
        message = server_message[prefix_end:server_message.index(constants.COMMAND_END_DELIM)].strip()
        return message
    
    # Listen for server input
    def run(self):
        """
        Driver of your IRC Client
        """
        logger.info('Thread: Client is listening')
        try:
            input_sources = [self.socket]
            while True:
                read_sockets, _write_sockets, _error_sockets = select.select(input_sources, [], [])
            
                # Receive messages from the server
                if read_sockets:
                    data = self.socket.recv(4096).decode(constants.COMMAND_ENCODING)
                    self.buffer += data
                    if constants.COMMAND_END_DELIM not in self.buffer:
                        logger.warning('Buffer does not contain CR-LF termination. Processing later.')
                    else:
                        message_delim = self.buffer.index(constants.COMMAND_END_DELIM) + len(constants.COMMAND_END_DELIM)
                        server_message = self.buffer[:message_delim]
                        self.buffer = self.buffer[message_delim:] # update buffer

                        logger.info(f'Client received message from the server {repr(server_message)}')
                        server_message = self.__process_server_message(server_message) # Process msg

                        logger.info(f'Displaying response "{server_message}"')
                        self.add_msg(server_message)

        except Exception as e:
            logger.warning(f'Thread: Listening Error {e}')
        

    def close(self):
        # Terminate connection
        logger.debug(f"Closing IRC Client object")
        self.socket.close()

def fetch_server_info(args):
    host = '127.0.0.1'
    port = 6667
    if(len(args) != 0 and (len(args) != 4 or args[0] != '--server' or args[2] != '--port' or not args[1].isnumeric() or not args[3].isnumeric())):
        print('Invalid argument list. Usage: irc_client.py [--server SERVER] [--port PORT]')
        sys.exit()
    if(len(args) == 4):
        host, port = args[1], int(args[3])
    return host, port


def main(args):
    host, port = fetch_server_info(args)

    # Pass args
    client = IRCClient(host, port)
    logger.info(f"Client object created")

    # Attempt connection with the server
    try:
        logger.info(f'Attempting connection with host {host} and port {port}')
        client.init_tcp_connection()
    except ConnectionRefusedError:
        conn_err = f'Server is not listening on {host}:{port}'
        logger.warning(conn_err)
        print(conn_err)
        sys.exit()

    # Connect to View
    logger.info(f'Successfully connected to {host}:{port}')
    with view.View() as v:
        logger.info(f"Entered the context of a View object")
        client.set_view(v)
        logger.debug(f"Passed View object to IRC Client")
        v.add_subscriber(client)
        logger.debug(f"IRC Client is subscribed to the View (to receive user input)")
        async def inner_run():
            await asyncio.gather(
                v.run(),
                return_exceptions=True,
            )
        try:
            threading.Thread(target=client.run, args=(), daemon=True).start()
            asyncio.run( inner_run() )
        except KeyboardInterrupt:
            logger.debug(f"Signifies end of process")
    client.close()

if __name__ == "__main__":
    main(sys.argv[1:])



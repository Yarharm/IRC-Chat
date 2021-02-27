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
    def __init__(self):
        self.global_channel = '#global'
        self.encoding = 'utf-8'

    def build(self, msg, request_type, prefix=''):
        request = ""

        if request_type == commands.BROADCAST:
            request = f'{commands.BROADCAST} {self.global_channel} :{msg}'
            request = f':{prefix} {request}' if prefix else request

        request += constants.MESSAGE_END_DELIM
        logger.info(f'RequestBuilder prepared request {repr(request)}')
        return request.encode(self.encoding)

class IRCClient(patterns.Subscriber):
    def __init__(self, host, port):
        super().__init__()
        self.nick = ''
        self._run = True
        self.host = host
        self.port = port
        self.socket = None
        self.request_builder = RequestBuilder()

    def set_view(self, view):
        self.view = view
    
    def add_msg(self, msg):
        self.view.add_msg(self.nick, msg)

    def init_tcp_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.setblocking(0)

    def update(self, msg):
        # Will need to modify this
        if not isinstance(msg, str):
            raise TypeError(f"Update argument needs to be a string")
        elif not len(msg):
            # Empty string
            return
        logger.info(f"IRCClient.update -> msg: {msg}")
        self.process_input(msg)

    def process_input(self, msg):
        request = ""
        if msg.lower().startswith('/quit'):
            raise KeyboardInterrupt
        elif msg.lower().startswith('/nick'):
            request = self.request_builder.build(msg, commands.NICKNAME)
        elif msg.lower().startswith('/user'):
            request = self.request_builder.build(msg, commands.USERNAME)
        else:
            request = self.request_builder.build(msg, commands.BROADCAST, self.nick)
        
        logger.info(f'Sending request {repr(request)}')
        self.socket.sendall(request)
    
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
                    data = self.socket.recv(4096).decode('utf-8')
                    if constants.MESSAGE_END_DELIM not in data:
                        logger.warning('Server response does not contain CR-LF termination')
                    if data:
                        logger.info(f'Client received message from the server {repr(data)}')
                        data = data[:data.index(constants.MESSAGE_END_DELIM)]
                        logger.info(f'Displaying response {data}')
                        self.add_msg(data)

        except Exception as e:
            logger.warning(f'Thread: Listening Error {e}')
        

    def close(self):
        # Terminate connection
        logger.debug(f"Closing IRC Client object")
        self.socket.close()

def fetch_server_info(args):
    host = '127.0.0.1'
    port = 6667
    if(len(args) != 0 and (len(args) != 4 or args[0] != '--server' or args[2] != '--port' or not args[1].isnumeric or not args[3].isnumeric())):
        print('Invalid argument list. Usage: irc_client.py [--server SERVER] [--port PORT]')
        sys.exit()
    if(len(args) == 4):
        host, port = args[1], int(args[3])
    return host, port


def main(args):
    host, port = fetch_server_info(args)

    # Pass your arguments where necessary
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
        except KeyboardInterrupt as e:
            logger.debug(f"Signifies end of process")
    client.close()

if __name__ == "__main__":
    # Parse your command line arguments here
    main(sys.argv[1:])



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

logging.basicConfig(filename='view.log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger()

class IRCClient(patterns.Subscriber):
    def __init__(self, host, port):
        super().__init__()
        self.username = str()
        self._run = True
        self.host = host
        self.port = port
        self.socket = None
        self.input_sources = [] # Sockets client reads from

    def set_view(self, view):
        self.view = view
    
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
        if msg.lower().startswith('/quit'):
            raise KeyboardInterrupt
        # elif msg.lower().startswith('/nick'):
        #     print(f'HERE {msg}')
        #     display_output = self.client.register_nickname(msg.split(' ')[-1])
        # elif msg.lower().startswith('/user'):
        #     display_output = self.client.register_username(msg.split(' ')[-1])
        logger.info(f'Sending message: {msg}')
        self.socket.sendall(msg.encode('utf-8'))
        

    def add_msg(self, msg):
        self.view.add_msg(self.username, msg)
    
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
                    if data:
                        logger.info(f'Thread: Client received message from the server "{data}"')
                        self.add_msg(data)

        except Exception as e:
            logger.info(f'Thread: ERR {e}')
        

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
        logger.info(conn_err)
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



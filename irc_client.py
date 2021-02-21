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

import patterns
import view
import sys
from socket_client import SocketClient

logging.basicConfig(filename='view.log', level=logging.DEBUG)
logger = logging.getLogger()


class IRCClient(patterns.Subscriber):

    def __init__(self, host, port):
        super().__init__()
        self.username = str()
        self._run = True
        self.client = SocketClient(host, port)

    def set_view(self, view):
        self.view = view
    
    def init_tcp_connection(self):
        self.client.init_connection()

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
        display_output = msg
        print('YPLO')
        if msg.lower().startswith('/quit'):
            raise KeyboardInterrupt
        elif msg.lower().startswith('/nick'):
            print(f'HERE {msg}')
            display_output = self.client.register_nickname(msg.split(' ')[-1])
        elif msg.lower().startswith('/user'):
            display_output = self.client.register_username(msg.split(' ')[-1])
        else:
            display_output = self.client.send_message(msg)
        self.add_msg(display_output)

    def add_msg(self, msg):
        self.view.add_msg(self.username, msg)

    async def run(self):
        """
        Driver of your IRC Client
        """

    def close(self):
        # Terminate connection
        logger.debug(f"Closing IRC Client object")
        self.client.close_connection()


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
    print(f'args {args}')
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
                client.run(),
                return_exceptions=True,
            )
        try:
            asyncio.run( inner_run() )
        except KeyboardInterrupt as e:
            logger.debug(f"Signifies end of process")
    client.close()

if __name__ == "__main__":
    # Parse your command line arguments here
    main(sys.argv[1:])

#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2021
#
# Distributed under terms of the MIT license.
import asyncio
import curses
import logging
import pathlib

import patterns

logging.basicConfig(filename='view.log', level=logging.DEBUG)
logger = logging.getLogger()


class View(patterns.Publisher):

    def __init__(self, **kwargs):
        super().__init__()
        # Kwargs extraction
        self.input_text = list()
        self.title = kwargs.get('title', None)

    def __enter__(self):
        self.stdscr = curses.initscr()
        self.stdscr.clear()
        self._loop = True # If set to False, stops it
        curses.noecho()
        curses.start_color()
        curses.cbreak(True)
        # Dimensions of windows
        self.height = curses.LINES
        self.width = curses.COLS
        # Colors
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE )
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN )
        self.stdscr.bkgd(curses.color_pair(1))
        self.stdscr.refresh()
        # Check minimum size for terminal
        if self.height < 5 and self.width < 100:
            raise Exception("Increase the size of the terminal")
        self._setup_title_win()
        self._setup_msg_win()
        self._setup_input_win()
        self.refresh()
        self._input_chrs = str() # Used to store intermediary inputs
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug(f"Exiting context and closing View object")
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        return True

    def _setup_title_win(self):
        self.title_win_begin = (0,0)
        self.title_win_dim = (1, self.width)
        self.title_win = curses.newwin(*self.title_win_dim, *self.title_win_begin)
        if self.title is None:
            title = "COMP445 - IRC Client"
        self.title = title.center(self.width-2)
        self.title_win.bkgd(curses.color_pair(2) | curses.A_BOLD)
        self.title_win.addstr(self.title)
        self.title_win.refresh()

    def _setup_msg_win(self):
        self.msg_win_begin = (1,0)
        self.msg_win_dim = (self.height - 2, self.width)
        self.msg_win = curses.newwin(*self.msg_win_dim, *self.msg_win_begin)
        self.msg_win.bkgd(curses.color_pair(1)|curses.A_ITALIC)
        self.msg_win.scrollok(True)
        self.msg_win.refresh()
        self._welcome_banner()

    def _welcome_banner(self):
        banner_file = pathlib.Path('banner.txt')
        if banner_file.is_file():
            with banner_file.open() as f:
                lines = f.readlines()
                max_len = max(map(len, lines))
                if max_len > self.width:
                    return
            line_shift = (self.width - 2 - max_len) // 2
            for l in lines:
                self.put_msg(" "*line_shift + l )

    def _setup_input_win(self):
        self.input_win_begin = (self.height - 1, 0)
        self.input_win_dim = (1, self.width)
        self.input_win = curses.newwin(*self.input_win_dim, *self.input_win_begin)
        self.input_win.bkgd(curses.color_pair(3))
        self.input_win.nodelay(True)
        self.input_win.refresh()

    def refresh(self):
        if hasattr(self, 'msg_win'):
            self.msg_win.refresh()
        if hasattr(self, 'input_win'):
            self.input_win.refresh()

    def get_input(self) -> bytes:
        k = self.input_win.getstr()
        input_str = k.decode().rstrip()
        self.input_win.clear()
        self.input_text.append(k)
        self.refresh()
        return k

    def add_msg(self, user: str, msg: str):
        self.put_msg(f"[{user}]: {msg}\n")

    def put_msg(self, msg):
        self.msg_win.addstr(msg)
        self.msg_win.refresh()

    def _input_getch(self):
        ch = self.input_win.getch()
        if ch == -1:
            # nothing inputed
            return
        logger.debug(f"Character int: {ch}")
        if ch < 9 or ch > 2**7:
            # non-ascii chars
            return
        elif ch == 127:
            # Delete char from input box
            # and from _input_chrs
            y,x = self.input_win.getyx()
            x = max(0, x-1)
            self.input_win.delch(y,x)
            self._input_chrs = self._input_chrs[:-1]
        elif ch == ord('\n'):
            # Notify listener
            pass
            logger.debug(f"Input line: {self._input_chrs}")
            self.notify(self._input_chrs)
            self._input_chrs = str()
            # Clear window
            self.input_win.clear()
        else:
            self._input_chrs += chr(ch)
            self.input_win.addch(ch)
            # for debugging
            #self.add_msg('chr', f"{ch} - " + chr(ch))

    async def run(self):
        """
        Loops and watches input_win 
        for user input and
        messages to write to msg_win
        """
        while True:
            try:
                self._input_getch()
                await asyncio.sleep(0.05)
            except KeyboardInterrupt:
                # KeyboardInterrupt signifies the end of the view
                logger.debug(f"KeyboardInterrupt detected within the view")
                raise

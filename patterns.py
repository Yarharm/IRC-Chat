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
import abc

class Publisher:

    def __init__(self):
        self.subscribers = list()

    def add_subscriber(self, s):
        self.subscribers.append(s)

    def rm_subscriber(self, s):
        try:
            self.subscribers.remove(s)
        except ValueError:
            # not present
            pass

    def notify(self, msg):
        for s in self.subscribers:
            if hasattr(s, 'update'):
                s.update(msg)

class Subscriber:

    @abc.abstractmethod
    def update(self, msg):
        pass

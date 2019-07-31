#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import os
import six


class Base(object):
    @staticmethod
    def _yes_no():
        print('[y/n]')
        choice = six.moves.input().lower()
        while choice not in ['y', 'n']:
            print('please respond with y or n')
            choice = six.moves.input().lower()
        return choice == 'y'

    @classmethod
    def _read_account(cls, config, name=None):
        name = name or cls.name
        if 'account' in config:
            if name in config['account']:
                return config['account'][name]
        return None

    @classmethod
    def _read_host(cls, config):
        if 'endpoint' in config:
            if cls.name in config['endpoint']:
                return config['endpoint'][cls.name]
        return None

    @classmethod
    def _read_token(cls, config):
        filename = cls.name + ".token"
        envname = cls.name.upper() + "_TOKEN"
        if config and 'token' in config and config['token'][cls.name]:
            return config['token'][cls.name]
        if envname in os.environ:
            return os.environ[envname]
        if os.path.isfile(filename):
            return open(filename, 'r').read().strip()
        raise Exception('no %s token provided!'
                        'please specify %s environment variable or create %s file' % (cls.name, envname, filename))

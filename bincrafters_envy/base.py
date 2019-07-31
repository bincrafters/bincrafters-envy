#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import os
import six
import fnmatch
import requests
import json
from abc import abstractmethod, ABCMeta


@six.add_metaclass(ABCMeta)
class Base(object):
    @abstractmethod
    def add(self, project_slug):
        raise NotImplementedError('"add" method is abstract')

    @abstractmethod
    def remove(self, project_slug, force):
        raise NotImplementedError('"remove" method is abstract')

    @abstractmethod
    def update(self, project_slug, env_vars, encrypted_vars):
        raise NotImplementedError('"update" method is abstract')

    @abstractmethod
    def add_one(self, project_slug):
        raise NotImplementedError('"add_one" method is abstract')

    @abstractmethod
    def remove_one(self, project_slug):
        raise NotImplementedError('"remove_one" method is abstract')

    @abstractmethod
    def exists(self, project_slug):
        raise NotImplementedError('"exists" method is abstract')

    def _get(self, **kwargs):
        return self._request(method="GET", **kwargs)

    def _post(self, **kwargs):
        return self._request(method="POST", **kwargs)

    def _delete(self, **kwargs):
        return self._request(method="DELETE", **kwargs)

    def _patch(self, **kwargs):
        return self._request(method="PATCH", **kwargs)

    def _put(self, **kwargs):
        return self._request(method="PUT", **kwargs)

    def _request(self, method, url, data=None, expected_status=200):
        url = self._endpoint + url
        r = requests.request(method=method, url=url, headers=self._headers, auth=self._auth, data=data)
        if r.status_code != expected_status:
            raise Exception('%s %s request failed %s %s' % (self.name, method, r.status_code, r.content))
        content_type = r.headers.get("Content-Type") or ""
        if "application/json" in content_type:
            # charmap' codec can't encode character '\u015f' in position 169832: character maps to <undefined>
            return json.loads(r.content.decode('utf-8', 'replace'))
        return r.content

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

    def remove(self, project_slug, force):
        projects = self.list()
        projects = [p for p in projects if fnmatch.fnmatch(p, project_slug)]
        if not projects:
            print("no projects matching %s pattern were found on %s" % (project_slug, self.name))
            return
        print("the following projects will be removed:")
        for p in projects:
            print(p)
        remove = force or self._yes_no()
        if remove:
            for p in projects:
                self.remove_one(p)

    def add(self, project_slug):
        if self.exists(project_slug):
            print('project %s already exists on %s' % (project_slug, self.name))
        else:
            print('adding project %s to %s' % (project_slug, self.name))

            self.add_one(project_slug)

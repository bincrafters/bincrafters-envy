#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import requests
import json

from .base import Base


class Appveyor(Base):
    name = "appveyor"
    default_host = 'https://ci.appveyor.com'

    def __init__(self, config, host):
        self._token = self._read_token(config)
        self._headers = {
            'Authorization': 'Bearer {token}'.format(token=self._token),
            'Content-type': 'application/json'
        }
        self._account = self._read_account(config) or 'BinCrafters'
        self._host = self._read_host(config) or host
        if self._token.startswith("v2.0"):
            self._endpoint = "{host}/api/account/{account}".format(host=self._host, account=self._account)
        else:
            self._endpoint = "{host}/api".format(host=self._host)
        self._github_account = self._read_account(config, "github") or 'bincrafters'

    def list(self):
        appveyor_url = '{endpoint}/projects'.format(endpoint=self._endpoint)
        r = requests.get(appveyor_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))

        # charmap' codec can't encode character '\u015f' in position 169832: character maps to <undefined>
        projects = json.loads(r.content.decode('utf-8', 'replace'))
        projects = [project['slug'] for project in projects]
        return projects

    def exists(self, project_slug):
        appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}'.format(host=self._host,
                                                                                accountName=self._account,
                                                                                projectSlug=project_slug)
        r = requests.get(appveyor_url, headers=self._headers)
        if r.status_code != 200:
            return False
        return True

    def add_one(self, project_slug):
        appveyor_url = '{endpoint}/projects'.format(endpoint=self._endpoint)
        repository_name = '{accountName}/{projectSlug}'.format(
            accountName=self._github_account,
            projectSlug=project_slug
        )

        request = dict()
        request['repositoryProvider'] = 'gitHub'
        request['repositoryName'] = repository_name
        r = requests.post(appveyor_url, data=json.dumps(request), headers=self._headers)
        if r.status_code != 200:
            raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))

    def remove_one(self, project_slug):
        appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}'.format(host=self._host,
                                                                                accountName=self._account,
                                                                                projectSlug=project_slug)
        r = requests.delete(appveyor_url, headers=self._headers)
        if r.status_code != 204:
            raise Exception('appveyor DELETE request failed %s %s' % (r.status_code, r.content))

    def update(self, project_slug, env_vars, encrypted_vars):
        appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}/settings/environment-variables'.format(
            host=self._host,
            accountName=self._account,
            projectSlug=project_slug.replace('_', '-')
        )

        r = requests.get(appveyor_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))
        appveyor_vars = json.loads(r.content.decode('utf-8', 'replace'))

        new_env_vars = dict()
        for k, v in env_vars.items():
            new_var = dict()
            new_var['name'] = k
            new_var['value'] = dict()
            if k in encrypted_vars:
                new_var['value']['value'] = self._encrypt(v)
                new_var['value']['isEncrypted'] = True
            else:
                new_var['value']['value'] = v
                new_var['value']['isEncrypted'] = False
            new_env_vars[k] = new_var

        for v in appveyor_vars:
            name = v['name']
            if name not in new_env_vars.keys():
                new_env_vars[name] = v

        request = []

        for _, v in new_env_vars.items():
            request.append(v)

        r = requests.put(appveyor_url, data=json.dumps(request), headers=self._headers)
        if r.status_code != 204:
            raise Exception('appveyor PUT request failed %s %s' % (r.status_code, r.content))

    def _encrypt(self, value):
        appveyor_url = '{endpoint}/account/encrypt'.format(endpoint=self._endpoint)
        request = dict()
        request['plainValue'] = value
        r = requests.post(appveyor_url, data=json.dumps(request), headers=self._headers)
        if r.status_code != 200:
            raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))
        return r.content.decode('utf-8', 'replace')

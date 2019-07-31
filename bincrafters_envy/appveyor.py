#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import json

from .base import Base


class Appveyor(Base):
    name = "appveyor"
    default_host = 'https://ci.appveyor.com'

    def __init__(self, config, host):
        self._auth = None
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
        projects = self._get(url='/projects')
        projects = [project['slug'] for project in projects]
        return projects

    def _project_url(self, project_slug):
        return '/projects/%s/%s' % (self._account, project_slug)

    def exists(self, project_slug):
        appveyor_url = self._project_url(project_slug)
        try:
            self._get(url=appveyor_url)
            return True
        except Exception:
            return False

    def add_one(self, project_slug):
        repository_name = '{accountName}/{projectSlug}'.format(
            accountName=self._github_account,
            projectSlug=project_slug
        )
        request = {
            'repositoryProvider': 'gitHub',
            'repositoryName': repository_name
        }
        self._post(url='/projects', data=json.dumps(request))

    def remove_one(self, project_slug):
        appveyor_url = self._project_url(project_slug)
        self._delete(url=appveyor_url, expected_status=204)

    def update(self, project_slug, env_vars, encrypted_vars):
        appveyor_url = '/projects/{accountName}/{projectSlug}/settings/environment-variables'.format(
            accountName=self._account,
            projectSlug=project_slug.replace('_', '-')
        )

        appveyor_vars = self._get(url=appveyor_url)

        new_env_vars = dict()
        for k, v in env_vars.items():
            new_var = {
                'name': k,
                "value": dict()
            }
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

        self._put(url=appveyor_url, data=json.dumps(request), expected_status=204)

    def _encrypt(self, value):
        appveyor_url = '/account/encrypt'
        request = {'plainValue': value}
        encrypted = self._post(url=appveyor_url, data=json.dumps(request))
        return encrypted.decode('utf-8', 'replace')

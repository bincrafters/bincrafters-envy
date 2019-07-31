#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import requests
import json

from .base import Base


class Travis(Base):
    name = "travis"
    default_host = 'https://api.travis-ci.com'

    def __init__(self, config, host):

        self._token = self._read_token(config)
        self._headers = {
            'User-Agent': 'Envy/1.0',
            'Accept': 'application/vnd.travis-ci.2+json',
            'Travis-API-Version': '3',
            'Content-Type': 'application/json',
            'Authorization': 'token {token}'.format(token=self._token)
        }
        self._account = self._read_account(config) or 'bincrafters'
        self._host = self._read_host(config) or host

    def exists(self, project_slug):
        travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
            host=self._host,
            accountName=self._account,
            projectSlug=project_slug
        )
        r = requests.get(travis_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))

        travis_vars = json.loads(r.content.decode('utf-8', 'replace'))
        return travis_vars['active']

    def list(self):
        travis_url = '{host}/owner/{accountName}/repos'.format(
            host=self._host,
            accountName=self._account
        )
        r = requests.get(travis_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))
        travis_projects = json.loads(r.content.decode('utf-8', 'replace'))
        projects = []
        for p in travis_projects['repositories']:
            slug = p['slug'].split('/')[1]
            projects.append(slug)
        return projects

    def add_one(self, project_slug):
        self._activate(project_slug)

    def remove_one(self, project_slug):
        self._activate(project_slug, False)

    def update(self, project_slug, env_vars, encrypted_vars):
        travis_url = '{host}/repo/{accountName}%2F{projectSlug}/env_vars'.format(
            host=self._host,
            accountName=self._account,
            projectSlug=project_slug
        )

        r = requests.get(travis_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))
        ids = dict()
        travis_vars = json.loads(r.content.decode('utf-8', 'replace'))
        for v in travis_vars['env_vars']:
            ids[v['name']] = v['id']

        for name, value in env_vars.items():
            request = dict()
            request['env_var.name'] = name
            request['env_var.value'] = value
            request['env_var.public'] = name not in encrypted_vars

            if name in ids.keys():
                travis_url_env = '{host}/repo/{accountName}%2F{projectSlug}/env_var/{id}'.format(
                    host=self._host,
                    accountName=self._account,
                    projectSlug=project_slug,
                    id=ids[name]
                )
                r = requests.patch(travis_url_env, data=json.dumps(request), headers=self._headers)
                if r.status_code != 200:
                    raise Exception('travis PATCH request failed %s %s' % (r.status_code, r.content))
            else:
                r = requests.post(travis_url, data=json.dumps(request), headers=self._headers)
                if r.status_code != 201:
                    raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))

    def _activate(self, project_slug, enable=True):
        travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
            host=self._host,
            accountName=self._account,
            projectSlug=project_slug
        )
        travis_url += '/activate' if enable else '/deactivate'
        r = requests.post(travis_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))

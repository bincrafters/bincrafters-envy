#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import json

from .base import Base


class Travis(Base):
    name = "travis"
    default_host = 'https://api.travis-ci.com'

    def __init__(self, config, host):

        self._auth = None
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
        self._endpoint = self._host

    def _project_url(self, project_slug):
        return '/repo/{accountName}%2F{projectSlug}'.format(
            accountName=self._account,
            projectSlug=project_slug
        )

    def exists(self, project_slug):
        project = self._get(url=self._project_url(project_slug))
        return project['active']

    def list(self):
        travis_url = '/owner/{accountName}/repos'.format(accountName=self._account)
        travis_projects = self._get(url=travis_url)
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
        travis_url = self._project_url(project_slug) + '/env_vars'
        travis_vars = self._get(url=travis_url)
        ids = dict()
        for v in travis_vars['env_vars']:
            ids[v['name']] = v['id']

        for name, value in env_vars.items():
            request = {
                'env_var.name': name,
                'env_var.value': value,
                'env_var.public': name not in encrypted_vars
            }
            if name in ids.keys():
                travis_url_env = self._project_url(project_slug) + '/env_var/' + ids[name]
                self._patch(url=travis_url_env, data=json.dumps(request))
            else:
                self._post(url=travis_url, data=json.dumps(request), expected_status=201)

    def _activate(self, project_slug, enable=True):
        travis_url = self._project_url(project_slug) + '/activate' if enable else '/deactivate'
        self._post(url=travis_url)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from .base import Base
import requests
import json
from requests.auth import HTTPBasicAuth


class Circle(Base):
    name = 'circle'
    default_host = 'https://circleci.com'

    def __init__(self, config, host):
        self._token = self._read_token(config)
        self._host = self._read_host(config) or host
        self._endpoint = self._host + "/api/v1.1"
        self._headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }
        self._auth = HTTPBasicAuth(username=self._token, password='')
        self._github_account = self._read_account(config, "github") or 'bincrafters'
        self._github_account = "SSE4"

    def list(self):
        url = self._endpoint + '/projects'
        r = requests.get(url, headers=self._headers, auth=self._auth)
        if r.status_code != 200:
            raise Exception('circle GET request failed %s %s' % (r.status_code, r.content))
        return [project["reponame"] for project in json.loads(r.content)]

    def _project_url(self, project_slug):
        return "{endpoint}/project/github/{username}/{project}".format(endpoint=self._endpoint,
                                                                       username=self._github_account,
                                                                       project=project_slug)

    def _activate(self, project_slug, enable=True):
        url = self._project_url(project_slug) + ("/follow" if enable else "/unfollow")

        r = requests.post(url, headers=self._headers, auth=self._auth)
        if r.status_code != 200:
            raise Exception('circle POST request failed %s %s' % (r.status_code, r.content))

    def add_one(self, project_slug):
        self._activate(project_slug)

    def remove_one(self, project_slug):
        self._activate(project_slug, False)

    def exists(self, project_slug):
        return project_slug in self.list()

    def update(self, project_slug, env_vars, encrypted_vars):
        url = self._project_url(project_slug) + "/envvar"
        r = requests.get(url, headers=self._headers, auth=self._auth)
        if r.status_code != 200:
            raise Exception('circle GET request failed %s %s' % (r.status_code, r.content))
        old_vars = json.loads(r.content)
        for var in old_vars:
            name = var["name"]
            if name not in env_vars:
                r = requests.delete(url + "/" + name, headers=self._headers, auth=self._auth)
                if r.status_code != 200:
                    raise Exception('circle GET request failed %s %s' % (r.status_code, r.content))

        for k, v in env_vars.items():
            request = dict()
            request["name"] = k
            request["value"] = v
            r = requests.post(url, headers=self._headers, auth=self._auth, data=json.dumps(request))
            if r.status_code != 201:
                raise Exception('circle POST request failed %s %s' % (r.status_code, r.content))

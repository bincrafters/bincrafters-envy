#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from .base import Base
import json
from requests.auth import HTTPBasicAuth


class Circle(Base):
    name = 'circle'
    default_host = 'https://circleci.com'

    def __init__(self, config, host):
        super(Circle, self).__init__(config, host)
        self._endpoint = self._host + "/api/v1.1"
        self._headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }
        self._auth = HTTPBasicAuth(username=self._token, password='')
        self._github_account = self._read_account(config, "github") or 'bincrafters'

    def list(self):
        projects = self._get(url='/projects')
        return [project["reponame"] for project in projects]

    def _project_url(self, project_slug):
        return "/project/github/{username}/{project}".format(username=self._github_account,
                                                             project=project_slug)

    def _activate(self, project_slug, enable=True):
        url = self._project_url(project_slug) + ("/follow" if enable else "/unfollow")
        self._post(url=url)

    def add_one(self, project_slug):
        self._activate(project_slug)

    def remove_one(self, project_slug):
        self._activate(project_slug, False)

    def exists(self, project_slug):
        return project_slug in self.list()

    def update(self, project_slug, env_vars, encrypted_vars):
        url = self._project_url(project_slug) + "/envvar"
        old_vars = self._get(url=url)
        for var in old_vars:
            name = var["name"]
            if name not in env_vars:
                self._delete(url=url + "/" + name)

        for k, v in env_vars.items():
            request = {"name": k, "value": v}
            self._post(url=url, json=request, expected_status=201)

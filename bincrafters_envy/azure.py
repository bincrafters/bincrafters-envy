#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from .base import Base
from requests.auth import HTTPBasicAuth
import json


class Azure(Base):
    name = "azure"
    default_host = "https://dev.azure.com"

    def __init__(self, config, host):
        super(Azure, self).__init__(config, host)

        self._account = self._read_account(config) or 'bincrafters'
        self._endpoint = self._host + '/' + self._account + "/packages/_apis"
        self._api_version = "?api-version=5.0"
        self._headers = {'Content-type': 'application/json'}
        self._auth = HTTPBasicAuth(username=self._token, password="")

    def add_one(self, project_slug):
        url = "/build/definitions" + self._api_version
        data = dict()
        data["process"] = {"type": 2, "yamlFilename": "./azure-pipelines.yml"}  # YAML
        data["name"] = "%s.%s" % (self._account, project_slug)
        data["type"] = "build"
        data["queueStatus"] = "enabled"
        data["processParameters"] = dict()
        data["drafts"] = []
        data["repository"] = dict()
        data["repository"]["id"] = "%s/%s" % (self._account, project_slug)
        data["repository"]["type"] = "GitHub"
        data["repository"]["url"] = "https://github.com/%s/%s.git" % (self._account, project_slug)
        data["repository"]["defaultBranch"] = "refs/heads/live"
        data["repository"]["clean"] = "false"
        data["repository"]["checkoutSubmodules"] = "false"

        self._post(url=url, data=json.dumps(data))
        pass

    def remove_one(self, project_slug):
        definitionid = self._find(project_slug)["value"][0]["id"]
        url = "/build/definitions/" + str(definitionid) + self._api_version
        self._delete(url=url, expected_status=204)

    def _find(self, project_slug):
        name = "%s.%s" % (self._account, project_slug)
        url = "/build/definitions" + self._api_version + "&name=%s" % name
        return self._get(url=url)

    def exists(self, project_slug):
        return self._find(project_slug)["count"] > 0

    def update(self, project_slug, env_vars, encrypted_vars):
        groupname = "%s.%s" % (self._account, project_slug)
        url = "/distributedtask/variablegroups" + self._api_version + "-preview.1"
        url += "&groupName=" + groupname

        data = {
            "type": "Vsts",
            "name": groupname,
            "description": "conan environment variables provided by envy",
            "variables": dict()
        }
        for name, value in env_vars.items():
            data["variables"][name] = {
                "value": value,
                "isSecret": name in encrypted_vars
            }
        groups = self._get(url=url)
        if groups["count"] > 0:
            groupid = groups["value"][0]["id"]
            url = "/distributedtask/variablegroups/" + str(groupid) + self._api_version + "-preview.1"
            self._put(url=url, data=json.dumps(data))
        else:
            url = "/distributedtask/variablegroups" + self._api_version + "-preview.1"
            self._post(url=url, data=json.dumps(data))

    def list(self):
        url = "/build/definitions" + self._api_version
        projects = self._get(url=url)
        # project name is in form "bincrafters.conan-qt", so we cut "bincrafters."
        projects = [p["name"][len(self._account) + 1:] for p in projects["value"]]
        return projects

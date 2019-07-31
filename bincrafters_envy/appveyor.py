import requests
import fnmatch
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
        self._host = host
        if self._token.startswith("v2.0"):
            self._endpoint = "{host}/api/account/{account}".format(host=self._host, account=self._account)
        else:
            self._endpoint = "{host}/api".format(host=self._host)
        self._github_account = self._read_account(config, "github") or 'bincrafters'

    def add(self, project_slug):
        appveyor_url = '{endpoint}/projects'.format(endpoint=self._endpoint)
        r = requests.get(appveyor_url, headers=self._headers)

        repository_name = '{accountName}/{projectSlug}'.format(
            accountName=self._github_account,
            projectSlug=project_slug
        )
        projects = json.loads(r.content.decode('utf-8', 'replace'))
        if r.status_code != 200:
            raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))

        found = False
        for project in projects:
            if project['repositoryName'] == repository_name:
                found = True
        if found:
            print('project %s already exists on appveyor' % project_slug)
        else:
            print('adding project %s to appveyor' % project_slug)

            request = dict()
            request['repositoryProvider'] = 'gitHub'
            request['repositoryName'] = repository_name
            r = requests.post(appveyor_url, data=json.dumps(request), headers=self._headers)
            if r.status_code != 200:
                raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))

    def remove(self, project_slug, force):
        appveyor_url = '{endpoint}/projects'.format(endpoint=self._endpoint)
        r = requests.get(appveyor_url, headers=self._headers)
        if r.status_code != 200:
            raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))
        # charmap' codec can't encode character '\u015f' in position 169832: character maps to <undefined>
        p = r.content.decode('utf-8', 'replace')
        appveyor_projects = json.loads(p)
        projects = [p['slug'] for p in appveyor_projects]
        projects = [p for p in projects if fnmatch.fnmatch(p, project_slug.replace('_', '-'))]
        if not projects:
            print("no projects matching %s pattern were found on appveyor" % project_slug)
            return
        print("the following projects will be removed:")
        for p in projects:
            print(p)
        remove = force or self._yes_no()
        if remove:
            for p in projects:
                appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}'.format(
                    host=self._host,
                    accountName=self._account,
                    projectSlug=p)
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

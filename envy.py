#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from configparser import ConfigParser
import requests
import json
import argparse
import sys


def travis_token():
    return open('travis.token', 'r').read().strip()


def appveyor_token():
    return open('appveyor.token', 'r').read().strip()

travis_host = 'https://api.travis-ci.org'
appveyor_host = 'https://ci.appveyor.com'

appveyor_headers = {
    'Authorization': 'Bearer {token}'.format(token=appveyor_token()),
    'Content-type': 'application/json'
}

travis_headers = {
    'User-Agent': 'Envy/1.0',
    'Accept': 'application/vnd.travis-ci.2+json',
    'Travis-API-Version': '3',
    'Content-Type': 'application/json',
    'Authorization': 'token {token}'.format(token=travis_token())
}


def add_to_appveyor(projectSlug):
    appveyor_url = '{host}/api/projects'.format(host=appveyor_host)
    r = requests.get(appveyor_url, headers=appveyor_headers)

    repository_name = '{accountName}/{projectSlug}'.format(
        accountName='bincrafters',
        projectSlug=projectSlug
    )
    projects = json.loads(r.content.decode())
    if r.status_code != 200:
        raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))

    found = False
    for project in projects:
        if project['repositoryName'] == repository_name:
            found = True
    if found:
        print('project %s already exists on appveyor' % projectSlug)
    else:
        print('adding project %s to appveyor' % projectSlug)

        request = dict()
        request['repositoryProvider'] = 'gitHub'
        request['repositoryName'] = repository_name
        r = requests.post(appveyor_url, data=json.dumps(request), headers=appveyor_headers)
        if r.status_code != 200:
            raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))


def add_to_travis(projectSlug):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
        host=travis_host,
        accountName='bincrafters',
        projectSlug=projectSlug
    )

    r = requests.get(travis_url, headers=travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))

    travis_vars = json.loads(r.content.decode())

    if travis_vars['active']:
        print('project %s already exists on travis' % projectSlug)
    else:
        print('adding project %s to travis' % projectSlug)

        travis_url += '/activate'
        r = requests.post(travis_url, headers=travis_headers)
        if r.status_code != 200:
            raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def update_travis(projectSlug, env_vars):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}/env_vars'.format(
        host=travis_host,
        accountName='bincrafters',
        projectSlug=projectSlug
    )

    r = requests.get(travis_url, headers=travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))
    ids = dict()
    travis_vars = json.loads(r.content.decode())
    for v in travis_vars['env_vars']:
        ids[v['name']] = v['id']

    for name, value in env_vars.items():
        request = dict()
        request['env_var.name'] = name
        request['env_var.value'] = value
        request['env_var.public'] = False

        if name in ids.keys():
            travis_url_env = '{host}/repo/{accountName}%2F{projectSlug}/env_var/{id}'.format(
                host=travis_host,
                accountName='bincrafters',
                projectSlug=projectSlug,
                id=ids[name]
            )
            r = requests.patch(travis_url_env, data=json.dumps(request), headers=travis_headers)
            if r.status_code != 200:
                raise Exception('travis PATCH request failed %s %s' % (r.status_code, r.content))
        else:
            r = requests.post(travis_url, data=json.dumps(request), headers=travis_headers)
            if r.status_code != 201:
                raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def update_appveyor(projectSlug, env_vars):
    appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}/settings/environment-variables'.format(
        host=appveyor_host,
        accountName='BinCrafters',
        projectSlug=projectSlug.replace('_', '-')
    )

    r = requests.get(appveyor_url, headers=appveyor_headers)
    if r.status_code != 200:
        raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))
    appveyor_vars = json.loads(r.content.decode())

    new_env_vars = env_vars.copy()

    for v in appveyor_vars:
        name = v['name']
        value = v['value']['value']
        new_env_vars[name] = value

    request = []

    for name, value in new_env_vars.items():
        var = dict()
        var['name'] = name
        var['value'] = dict()
        var['value']['isEncrypted'] = False
        var['value']['value'] = value
        request.append(var)

    r = requests.put(appveyor_url, data=json.dumps(request), headers=appveyor_headers)
    if r.status_code != 204:
        raise Exception('appveyor PUT request failed %s %s' % (r.status_code, r.content))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='envy: update environment variables on travis and appveyor')
    parser.add_argument('-p', action='store', dest='project', type=str, required=True,
                        help='GitHub project name (aka projectSlug)')
    parser.add_argument('--skip-travis', action='store_true', dest='skip_travis',
                        help='skip travis configuration')
    parser.add_argument('--skip-apveyor', action='store_true', dest='skip_appveyor',
                        help='skip appveyor configuration')
    parser.set_defaults(skip_travis=False)
    parser.set_defaults(skip_appveyor=False)
    args = parser.parse_args()

    env_vars = dict()
    config = ConfigParser()
    config.optionxform = str
    config.read('env.ini')
    for k, v in config['env'].items():
        env_vars[k] = v

    failed = False

    if not args.skip_travis:
        try:
            print('updating travis...')
            add_to_travis(args.project)
            update_travis(args.project, env_vars)
            print('updating travis...OK')
        except Exception as e:
            print('updating travis...FAIL %s' % e)
            failed = True

    if not args.skip_appveyor:
        try:
            print('updating appveyor...')
            add_to_appveyor(args.project)
            update_appveyor(args.project, env_vars)
            print('updating appveyor...OK')
        except Exception as e:
            print('updating appveyor...FAIL %s' % e)
            failed = True

    sys.exit(1 if failed else 0)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from configparser import ConfigParser
import requests
import json
import argparse
import sys
import os


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


def add_to_appveyor(project_slug):
    appveyor_url = '{host}/api/projects'.format(host=appveyor_host)
    r = requests.get(appveyor_url, headers=appveyor_headers)

    repository_name = '{accountName}/{projectSlug}'.format(
        accountName='bincrafters',
        projectSlug=project_slug
    )
    projects = json.loads(r.content.decode())
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
        r = requests.post(appveyor_url, data=json.dumps(request), headers=appveyor_headers)
        if r.status_code != 200:
            raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))


def add_to_travis(project_slug):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
        host=travis_host,
        accountName='bincrafters',
        projectSlug=project_slug
    )

    r = requests.get(travis_url, headers=travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))

    travis_vars = json.loads(r.content.decode())

    if travis_vars['active']:
        print('project %s already exists on travis' % project_slug)
    else:
        print('adding project %s to travis' % project_slug)

        travis_url += '/activate'
        r = requests.post(travis_url, headers=travis_headers)
        if r.status_code != 200:
            raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def update_travis(project_slug, env_vars):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}/env_vars'.format(
        host=travis_host,
        accountName='bincrafters',
        projectSlug=project_slug
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
                projectSlug=project_slug,
                id=ids[name]
            )
            r = requests.patch(travis_url_env, data=json.dumps(request), headers=travis_headers)
            if r.status_code != 200:
                raise Exception('travis PATCH request failed %s %s' % (r.status_code, r.content))
        else:
            r = requests.post(travis_url, data=json.dumps(request), headers=travis_headers)
            if r.status_code != 201:
                raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def appveyor_encrypt(value):
    appveyor_url = '{host}/api/account/encrypt'.format(host=appveyor_host)
    request = dict()
    request['plainValue'] = value
    r = requests.post(appveyor_url, data=json.dumps(request), headers=appveyor_headers)
    if r.status_code != 200:
        raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))
    return r.content.decode()


def update_appveyor(project_slug, env_vars):
    appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}/settings/environment-variables'.format(
        host=appveyor_host,
        accountName='BinCrafters',
        projectSlug=project_slug.replace('_', '-')
    )

    r = requests.get(appveyor_url, headers=appveyor_headers)
    if r.status_code != 200:
        raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))
    appveyor_vars = json.loads(r.content.decode())

    new_env_vars = dict()
    for k, v in env_vars.items():
        new_var = dict()
        new_var['name'] = k
        new_var['value'] = dict()
        new_var['value']['value'] = appveyor_encrypt(v)
        new_var['value']['isEncrypted'] = True
        new_env_vars[k] = new_var

    for v in appveyor_vars:
        name = v['name']
        if name not in new_env_vars.keys():
            new_env_vars[name] = v

    request = []

    for _, v in new_env_vars.items():
        request.append(v)

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

    if not os.path.isfile('env.ini'):
        print('env.ini file is missing, please create one (see env.ini.example for the details)')
        sys.exit(1)

    if not os.path.isfile('appveyor.token'):
        print('appveyor.token file is missing, please create one (see README.MD for the details')
        sys.exit(1)

    if not os.path.isfile('travis.token'):
        print('travis.token file is missing, please create one (see README.MD for the details')
        sys.exit(1)

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

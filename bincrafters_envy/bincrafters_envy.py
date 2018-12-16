#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from configparser import ConfigParser
import requests
import json
import argparse
import sys
import os
import fnmatch

__author__  = "BinCrafters"
__license__ = "MIT"
__version__ = '0.1.3'


def travis_token(config, filename):
    if config and 'token' in config and config['token']['travis']:
        return config['token']['travis']
    if 'TRAVIS_TOKEN' in os.environ:
        return os.environ['TRAVIS_TOKEN']
    if os.path.isfile(filename):
        return open(filename, 'r').read().strip()
    raise Exception('no travis token provided!'
                    'please specify TRAVIS_TOKEN environment variable or create %s file' % filename)


def appveyor_token(config, filename):
    if config and 'token' in config and config['token']['appveyor']:
        return config['token']['appveyor']
    if 'APPVEYOR_TOKEN' in os.environ:
        return os.environ['APPVEYOR_TOKEN']
    if os.path.isfile(filename):
        return open(filename, 'r').read().strip()
    raise Exception('no appveyor token provided!'
                    'please specify APPVEYOR_TOKEN environment variable or create %s file' % filename)


this = sys.modules[__name__]
this.travis_host = ''
this.appveyor_host = ''

this.appveyor_headers = dict()
this.travis_headers = dict()

this.travis_account = 'bincrafters'
this.appveyor_account = 'BinCrafters'
this.github_account = 'bincrafters'

this.appveyor_v2_api = False


def appveyor_endpoint():
    if this.appveyor_v2_api:
        return "{host}/api/account/{account}".format(host=this.appveyor_host, account=this.appveyor_account)
    else:
        return "{host}/api".format(host=this.appveyor_host)


def add_to_appveyor(project_slug):
    appveyor_url = '{endpoint}/projects'.format(endpoint=appveyor_endpoint())
    r = requests.get(appveyor_url, headers=this.appveyor_headers)

    repository_name = '{accountName}/{projectSlug}'.format(
        accountName=this.github_account,
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
        r = requests.post(appveyor_url, data=json.dumps(request), headers=this.appveyor_headers)
        if r.status_code != 200:
            raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))


def travis_activate(project_slug, activate):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
        host=this.travis_host,
        accountName=travis_account,
        projectSlug=project_slug
    )
    travis_url += '/activate' if activate else '/deactivate'
    r = requests.post(travis_url, headers=this.travis_headers)
    if r.status_code != 200:
        raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def add_to_travis(project_slug):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
        host=this.travis_host,
        accountName=this.travis_account,
        projectSlug=project_slug
    )

    r = requests.get(travis_url, headers=this.travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))

    travis_vars = json.loads(r.content.decode('utf-8', 'replace'))

    if travis_vars['active']:
        print('project %s already exists on travis' % project_slug)
    else:
        print('adding project %s to travis' % project_slug)

        travis_activate(project_slug, True)


def update_travis(project_slug, env_vars, encrypted_vars):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}/env_vars'.format(
        host=this.travis_host,
        accountName=this.travis_account,
        projectSlug=project_slug
    )

    r = requests.get(travis_url, headers=this.travis_headers)
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
                host=this.travis_host,
                accountName=this.travis_account,
                projectSlug=project_slug,
                id=ids[name]
            )
            r = requests.patch(travis_url_env, data=json.dumps(request), headers=this.travis_headers)
            if r.status_code != 200:
                raise Exception('travis PATCH request failed %s %s' % (r.status_code, r.content))
        else:
            r = requests.post(travis_url, data=json.dumps(request), headers=this.travis_headers)
            if r.status_code != 201:
                raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


def appveyor_encrypt(value):
    appveyor_url = '{endpoint}/account/encrypt'.format(endpoint=appveyor_endpoint())
    request = dict()
    request['plainValue'] = value
    r = requests.post(appveyor_url, data=json.dumps(request), headers=this.appveyor_headers)
    if r.status_code != 200:
        raise Exception('appveyor POST request failed %s %s' % (r.status_code, r.content))
    return r.content.decode('utf-8', 'replace')


def update_appveyor(project_slug, env_vars, encrypted_vars):
    appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}/settings/environment-variables'.format(
        host=this.appveyor_host,
        accountName=this.appveyor_account,
        projectSlug=project_slug.replace('_', '-')
    )

    r = requests.get(appveyor_url, headers=this.appveyor_headers)
    if r.status_code != 200:
        raise Exception('appveyor GET request failed %s %s' % (r.status_code, r.content))
    appveyor_vars = json.loads(r.content.decode('utf-8', 'replace'))

    new_env_vars = dict()
    for k, v in env_vars.items():
        new_var = dict()
        new_var['name'] = k
        new_var['value'] = dict()
        if k in encrypted_vars:
            new_var['value']['value'] = appveyor_encrypt(v)
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

    r = requests.put(appveyor_url, data=json.dumps(request), headers=this.appveyor_headers)
    if r.status_code != 204:
        raise Exception('appveyor PUT request failed %s %s' % (r.status_code, r.content))


def yes_no():
    print('[y/n]')
    choice = raw_input().lower()
    while choice not in ['y', 'n']:
        print('please respond with y or n')
        choice = raw_input().lower()
    return choice == 'y'


def remove_from_travis(project_slug, force):
    travis_url = '{host}/owner/{accountName}/repos'.format(
        host=this.travis_host,
        accountName=this.travis_account
    )
    r = requests.get(travis_url, headers=this.travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))
    travis_projects = json.loads(r.content.decode('utf-8', 'replace'))
    projects = []
    for p in travis_projects['repositories']:
        slug = p['slug'].split('/')[1]
        projects.append(slug)
    projects = [p for p in projects if fnmatch.fnmatch(p, project_slug)]
    if not projects:
        print("no projects matching %s pattern were found on appveyor" % project_slug)
        return
    print("the following projects will be removed:")
    for p in projects:
        print(p)
    remove = force or yes_no()
    if remove:
        for p in projects:
            print('deactivate', p)
            travis_activate(p, False)


def remove_from_appveyor(project_slug, force):
    appveyor_url = '{endpoint}/projects'.format(endpoint=appveyor_endpoint())
    r = requests.get(appveyor_url, headers=this.appveyor_headers)
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
    remove = force or yes_no()
    if remove:
        for p in projects:
            appveyor_url = '{host}/api/projects/{accountName}/{projectSlug}'.format(
                host=this.appveyor_host,
                accountName=this.appveyor_account,
                projectSlug=p)
            r = requests.delete(appveyor_url, headers=this.appveyor_headers)
            if r.status_code != 204:
                raise Exception('appveyor DELETE request failed %s %s' % (r.status_code, r.content))


def main(args):
    parser = argparse.ArgumentParser(description='update environment variables on travis and appveyor')
    parser.add_argument('-p', '--project', action='append', dest='projects', type=str, required=True,
                        help='GitHub project name (aka projectSlug)')
    parser.add_argument('--skip-travis', action='store_true', dest='skip_travis',
                        help='skip travis configuration')
    parser.add_argument('--skip-appveyor', action='store_true', dest='skip_appveyor',
                        help='skip appveyor configuration')
    parser.add_argument('-r', '--remove', action='store_true', dest='remove',
                        help='remove specified project(s)')
    parser.add_argument('-f', '--force', action='store_true', dest='force',
                        help='force removal for all projects (no confirmation)')
    parser.add_argument('-c', '--config', type=str, default='envy.ini',
                        help='configuration INI file name')
    parser.add_argument('-t', '--travis-token-file', type=str, default='travis.token',
                        help='name of the file containing travis token')
    parser.add_argument('-a', '--appveyor-token-file', type=str, default='appveyor.token',
                        help='name of the file containing appveyortoken')
    parser.add_argument('-e', '--env', action='append', dest='env', type=str,
                        help='additional environment variables')
    parser.add_argument('--travis-host', dest='travis_host', type=str, default='https://api.travis-ci.com',
                        help='endpoint for travis REST API')
    parser.add_argument('--appveyor-host', dest='appveyor_host', type=str, default='https://ci.appveyor.com',
                        help='endpoint for appveyor REST API')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.set_defaults(skip_travis=False)
    parser.set_defaults(skip_appveyor=False)
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print('%s file is missing, please create one (see env.ini.example for the details)' % args.config)
        sys.exit(1)

    env_vars = dict()
    config = ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read(args.config)

    if not args.skip_travis:
        token = travis_token(config, args.travis_token_file)
        this.travis_headers = {
            'User-Agent': 'Envy/1.0',
            'Accept': 'application/vnd.travis-ci.2+json',
            'Travis-API-Version': '3',
            'Content-Type': 'application/json',
            'Authorization': 'token {token}'.format(token=token)
        }
        this.travis_host = args.travis_host

    if not args.skip_appveyor:
        token = appveyor_token(config, args.appveyor_token_file)
        this.appveyor_headers = {
            'Authorization': 'Bearer {token}'.format(token=token),
            'Content-type': 'application/json'
        }
        this.appveyor_host = args.appveyor_host
        this.appveyor_v2_api = token.startswith("v2.0")

    for k, v in config['env'].items():
        env_vars[k] = v

    if args.env:
        for e in args.env:
            k, v = e.split('=')
            env_vars[k] = v

    encrypted_vars = []
    for k, _ in config['encrypted'].items():
        encrypted_vars.append(k)

    if 'account' in config:
        this.travis_account = config['account']['travis'] or this.travis_account
        this.appveyor_account = config['account']['appveyor'] or this.appveyor_account
        this.github_account = config['account']['github'] or this.github_account

    failed = False

    for project in args.projects:

        if not args.skip_travis:
            try:
                print('updating project %s on travis...' % project)
                if args.remove:
                    remove_from_travis(project, args.force)
                else:
                    add_to_travis(project)
                    update_travis(project, env_vars, encrypted_vars)
                print('updating project %s on travis...OK' % project)
            except Exception as e:
                print('updating project %s on travis...FAIL\n%s' % (project, e))
                failed = True

        if not args.skip_appveyor:
            try:
                print('updating project %s on appveyor...' % project)
                if args.remove:
                    remove_from_appveyor(project, args.force)
                else:
                    add_to_appveyor(project)
                    update_appveyor(project, env_vars, encrypted_vars)
                print('updating project %s on appveyor...OK' % project)
            except Exception as e:
                print('updating project %s on appveyor...FAIL\n%s' % (project, e))
                failed = True

    sys.exit(1 if failed else 0)

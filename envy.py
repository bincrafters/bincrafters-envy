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


def travis_token():
    if 'TRAVIS_TOKEN' in os.environ:
        return os.environ['TRAVIS_TOKEN']
    if os.path.isfile('travis.token'):
        return open('travis.token', 'r').read().strip()
    raise Exception('no travis token provided!'
                    'please specify TRAVIS_TOKEN environment variable or create travis.token file')


def appveyor_token():
    if 'APPVEYOR_TOKEN' in os.environ:
        return os.environ['APPVEYOR_TOKEN']
    if os.path.isfile('appveyor.token'):
        return open('appveyor.token', 'r').read().strip()
    raise Exception('no appveyor token provided!'
                    'please specify APPVEYOR_TOKEN environment variable or create appveyor.token file')


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


def travis_activate(project_slug, activate):
    travis_url = '{host}/repo/{accountName}%2F{projectSlug}'.format(
        host=travis_host,
        accountName='bincrafters',
        projectSlug=project_slug
    )
    travis_url += '/activate' if activate else '/deactivate'
    r = requests.post(travis_url, headers=travis_headers)
    if r.status_code != 200:
        raise Exception('travis POST request failed %s %s' % (r.status_code, r.content))


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

        travis_activate(project_slug, True)


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


def yes_no():
    print('[y/n]')
    choice = input().lower()
    while choice not in ['y', 'n']:
        print('please respond with y or n')
        choice = raw_input().lower()
    return choice == 'y'


def remove_from_travis(project_slug, force):
    travis_url = '{host}/owner/{accountName}/repos'.format(
        host=travis_host,
        accountName='bincrafters'
    )
    r = requests.get(travis_url, headers=travis_headers)
    if r.status_code != 200:
        raise Exception('travis GET request failed %s %s' % (r.status_code, r.content))
    travis_projects = json.loads(r.content.decode())
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
    appveyor_url = '{host}/api/projects'.format(host=appveyor_host)
    r = requests.get(appveyor_url, headers=appveyor_headers)
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
                host=appveyor_host,
                accountName='BinCrafters',
                projectSlug=p)
            r = requests.delete(appveyor_url, headers=appveyor_headers)
            if r.status_code != 204:
                raise Exception('appveyor DELETE request failed %s %s' % (r.status_code, r.content))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='envy: update environment variables on travis and appveyor')
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

    for project in args.projects:

        if not args.skip_travis:
            try:
                print('updating project %s on travis...' % project)
                if args.remove:
                    remove_from_travis(project, args.force)
                else:
                    add_to_travis(project)
                    update_travis(project, env_vars)
                print('updating project %s on travis...OK' % project)
            except Exception as e:
                print('updating project %s on travis...FAIL %s' % (project, e))
                failed = True

        if not args.skip_appveyor:
            try:
                print('updating project %s on appveyor...' % project)
                if args.remove:
                    remove_from_appveyor(project, args.force)
                else:
                    add_to_appveyor(project)
                    update_appveyor(project, env_vars)
                print('updating project %s on appveyor...OK' % project)
            except Exception as e:
                print('updating project %s on appveyor...FAIL %s' % (project, e))
                failed = True

    sys.exit(1 if failed else 0)

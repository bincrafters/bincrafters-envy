#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import argparse
import sys
import os
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

from .appveyor import Appveyor
from .travis import Travis
from .circle import Circle

__author__ = "BinCrafters"
__license__ = "MIT"
__version__ = '0.1.7'


def main(args):
    parser = argparse.ArgumentParser(description='update environment variables on travis and appveyor')
    parser.add_argument('-p', '--project', action='append', dest='projects', type=str, required=True,
                        help='GitHub project name (aka projectSlug)')
    parser.add_argument('--skip-travis', action='store_true', dest='skip_travis',
                        help='skip travis configuration')
    parser.add_argument('--skip-appveyor', action='store_true', dest='skip_appveyor',
                        help='skip appveyor configuration')
    parser.add_argument('--skip-circle', action='store_true', dest='skip_circle',
                        help='skip circle configuration')
    parser.add_argument('-r', '--remove', action='store_true', dest='remove',
                        help='remove specified project(s)')
    parser.add_argument('-f', '--force', action='store_true', dest='force',
                        help='force removal for all projects (no confirmation)')
    parser.add_argument('-c', '--config', type=str, default='env.ini',
                        help='configuration INI file name')
    parser.add_argument('-t', '--travis-token-file', type=str, default='travis.token',
                        help='name of the file containing travis token')
    parser.add_argument('-a', '--appveyor-token-file', type=str, default='appveyor.token',
                        help='name of the file containing appveyortoken')
    parser.add_argument('-e', '--env', action='append', dest='env', type=str,
                        help='additional environment variables')
    parser.add_argument('--travis-host', dest='travis_host', type=str, default=Travis.default_host,
                        help='endpoint for travis REST API')
    parser.add_argument('--appveyor-host', dest='appveyor_host', type=str, default=Appveyor.default_host,
                        help='endpoint for appveyor REST API')
    parser.add_argument('--circle-host', dest='circle_host', type=str, default=Circle.default_host,
                        help='endpoint for circle REST API')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.set_defaults(skip_travis=False)
    parser.set_defaults(skip_appveyor=False)
    args = parser.parse_args(args)

    config_path = args.config
    print("args", args.config)
    if not os.path.isfile(config_path):
        user_home = os.environ.get("HOME", os.environ.get("USERPROFILE", os.path.expanduser("~")))
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(user_home, ".config"))
        xdg_config_path = os.path.join(xdg_config_home, "bincrafters-envy", config_path)
        if not os.path.isabs(config_path) and os.path.isfile(xdg_config_path):
            config_path = xdg_config_path
        else:
            print('%s file is missing, please create one (see env.ini.example for the details)' % args.config)
            sys.exit(1)
    print("using config: %s" % config_path)

    env_vars = dict()
    config = ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read(config_path)

    for k, v in config['env'].items():
        env_vars[k] = v

    if args.env:
        for e in args.env:
            k, v = e.split('=')
            env_vars[k] = v

    encrypted_vars = []
    for k, _ in config['encrypted'].items():
        encrypted_vars.append(k)

    failed = False

    ci_systems = []
    if not args.skip_travis:
        ci_systems.append(Travis(config, args.travis_host))
    if not args.skip_appveyor:
        ci_systems.append(Appveyor(config, args.appveyor_host))
    if not args.skip_circle:
        ci_systems.append(Circle(config, args.circle_host))

    for project in args.projects:
        for ci_system in ci_systems:
            try:
                print('updating project %s on %s...' % (project, ci_system.name))
                if args.remove:
                    ci_system.remove(project, args.force)
                else:
                    ci_system.add(project)
                    ci_system.update(project, env_vars, encrypted_vars)
                print('updating project %s on %s...OK' % (project, ci_system.name))
            except Exception as e:
                print('updating project %s on %s...FAIL\n%s' % (project, ci_system.name, e))
                failed = True

    sys.exit(1 if failed else 0)

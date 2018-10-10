#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bincrafters_envy import bincrafters_envy
import os


def test_travis_token():
    os.environ['TRAVIS_TOKEN'] = 'foobar'
    assert bincrafters_envy.travis_token(None, 'test.ini') == 'foobar'

def test_appveyor_token():
    os.environ['APPVEYOR_TOKEN'] = 'foobar'
    assert bincrafters_envy.appveyor_token(None, 'test.ini') == 'foobar'

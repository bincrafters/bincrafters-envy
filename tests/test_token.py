#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bincrafters_envy import bincrafters_envy
import os


def test_token():
    os.environ['TRAVIS_TOKEN'] = 'foobar'
    assert bincrafters_envy.travis_token('test.ini') == 'foobar'

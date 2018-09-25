#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
if sys.version_info.major == 3:
    from bincrafters_envy import bincrafters_envy
else:
    import bincrafters_envy


def run():
    bincrafters_envy.main(sys.argv[1:])


if __name__ == '__main__':
    run()

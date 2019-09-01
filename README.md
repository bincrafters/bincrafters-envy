[![Build Status](https://travis-ci.org/bincrafters/bincrafters-envy.svg?branch=master)](https://travis-ci.org/bincrafters/bincrafters-envy)
[![Build status](https://ci.appveyor.com/api/projects/status/bb3844r6mnu7gy1g?svg=true)](https://ci.appveyor.com/project/BinCrafters/bincrafters-envy)
[![codecov](https://codecov.io/gh/bincrafters/bincrafters-envy/branch/master/graph/badge.svg)](https://codecov.io/gh/bincrafters/bincrafters-envy)
[![download](https://img.shields.io/badge/download-pypi-blue.svg)](https://pypi.org/project/bincrafters-envy)

# Bincrafters Envy

Update environment variables for travis, appveyor, Azure DevOps Pipelines and Circle CI.

#### Install
To install using pypi.org:

    pip install bincrafters-envy

#### Usage
first, you'll need to obtain API tokens:

to obtain appveyor token, visit this [page](https://ci.appveyor.com/api-keys)

to obtain travis token (for travis-ci.com), visit this [page](https://travis-ci.com/account/preferences)

to obtain travis token (for travis-ci.org), visit this [page](https://travis-ci.org/account/preferences)

to obtain AZP (Azure DevOps Pipelines) token, visit this [page](https://dev.azure.com/bincrafters/_usersSettings/tokens)

to obtain Circle CI token, visit this [page](https://circleci.com/account/api)

create **env.ini** file with your environment variables (take a look at the **env.ini.example**):

```
[account]
appveyor = <your account name on appveyor>
travis = <your account name on travis>
github = <your account name on GitHub>
azure = <your account name on Azure>
circle = <your account name on Circle CI>
[token]
appveyor = <your appveyor token>
travis = <your travis token>
azure = <your Azure DevOps Pipelines token>
circle = <you Circle CI token>
[env]
CONAN_LOGIN_USERNAME = <your username>
CONAN_PASSWORD = <your password>
[encrypted]
CONAN_PASSWORD
```

then run `python envy.py -p <project>` (e.g. `python envy.py -p conan-libastral`)

the `env.ini` configuration file is read from the `$XDG_CONFIG_HOME/.bincrafters-envy/env.ini` by default.

#### Testing
To run all unit tests:

    cd tests
    pytest -v -s --cov=bincrafters_envy

#### LICENSE
[MIT](LICENSE)

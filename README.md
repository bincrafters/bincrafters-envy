# Bincrafters Envy

#### Update environment variables for travis and appveyor

## usage
first, you'll need to obtains travis and appveyor tokens

to obtain appveyor token, visit this [page](https://ci.appveyor.com/api-token)

to obtain travis token, install travis [ruby client](https://github.com/travis-ci/travis.rb), then run:

`travis login'

'travis token`

put your appveyor token into file named **appveyor.token**

put your travis token into file named **travis.token**

create **env.ini** file with your environment variables (take a look at the **env.ini.example**):

```
[env]
CONAN_LOGIN_USERNAME = <your username>
CONAN_PASSWORD = <your password>
```

then run `python envy.py -p <project>` (e.g. `python envy.py -p conan-libastral`)

#### LICENSE
[MIT](LICENSE)

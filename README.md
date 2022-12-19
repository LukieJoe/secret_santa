# secret_santa

A simple auto emailer for secret santa<br/>

initial setup
```
source ./venv/bin/activate
pip install -r requirements.txt
```

required ENV
```
export SANTA_EMAIL=<gmail>
export SANTA_GROUP=<DBNAME>
export SANTA_CONTENT=<template for full email>
export SANTA_TEST_CONTENT=<template for test email>
export SANTA_OAUTH=<path to secrets file>
export SANTA_DB_PATH=<path to database>
```

setup db and add each participant
```
./dbtool.py create <DBNAME>
SANTA_GROUP=<DBNAME> ./dbtool.py <name> <email>
```

sample usage. remove `r` flag for dry run
```
./secret_santa -z           # get token secrets for SANTA_EMAIL and dump into SANTA_OAUTH, must happen first
./secret_santa -rts <email> # send test content to email
./secret_santa -rfs <email> # send full content to email
./secret_santa -rt          # send the test content to all participants
./secret_santa -rf          # send the full content to all participants
./secret_santa -rx <email>  # resend content for <email> to <email> with some spite
```

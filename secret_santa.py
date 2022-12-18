#!/usr/bin/env python3

import yagmail
from imbox import Imbox

from random import shuffle
from time import sleep
from datetime import datetime
from sys import argv
from os import getenv
import sqlite3
from contextlib import closing
from getopt import getopt

DRYRUN = (getenv('SANTA_TEST_CONTENT'), False)
FULL_CONTENT = (getenv('SANTA_CONTENT'), True)

CLIENT = True
DEBUG = True
CONTENT, ASSIGN_PAIRS = DRYRUN

GROUP = getenv('SANTA_GROUP')
EMAIL = getenv('SANTA_EMAIL')
OAUTH = getenv('SANTA_OAUTH') if getenv('SANTA_OAUTH') else '.santa/oauth2_cred.json'
DB_PATH = getenv('SANTA_DB_PATH') if getenv('SANTA_DB_PATH') else '.santa/santaslist.db'

class SecretSanta:
    db = sqlite3.connect(DB_PATH)

    participants = dict()
    pairs = []

    def __init__(self):
        with closing(self.db.cursor()) as c:
            c.execute('SELECT * FROM %s' % (GROUP,))
            # dict of name -> email
            self.participants = dict( c.fetchall() )

        self.roll()
        self.send_pairs()

    def roll(self):
        names = [x for x in self.participants]
        pairs = []
        while not len(pairs) is len(names):
            del pairs[:] # clear list
            b = names.copy() # deep copy
            for x in names:
                shuffle(b) # shuffle b
                if not x is b[-1]:
                    pairs.append((x,b.pop())) # remove item in b taken

        self.pairs = pairs

        if DEBUG: print("%s\n" % self.pairs)

    def send_pairs(self):
        for pair in self.pairs:
            to = self.participants[pair[0]]      # get left email
            subject = "FROM SANTA!! %s" % year() # prevent weird reply nonsense
            body = get_pair(get_content(), pair) # if ASSIGN_PAIRS get_content() % pair

            send(to, subject, body)

def year():
    return datetime.now().date().year

def get_content():
    c = ''
    with open(CONTENT) as f:
        for line in f: c += line
    return c

def get_pair(c, p):
    return c % p if ASSIGN_PAIRS else c

def send(to, subj, body):
    if DEBUG: print(to, subj, body)
    else:
        yagmail.SMTP( EMAIL, oauth2_file=OAUTH )\
               .send( to, subj, body )
        print( 'SENT to ', to )

if __name__ == '__main__':

    state_format = 'CLIENT(%s) DEBUG(%s) CONTENT(%s) PAIRED(%s) EMAIL(%s) GROUP(%s)\n'

    usage = ['help', 'with-client', 'no-client', 'test', 'full', 'debug', 'release', 'send=', 'content=', 'paired', 'unpaired', 'group']
    opts, _ = getopt(argv[1:], 'hwntfdrs:c:pug:', usage)
    for k,v in opts:
        if k in ('-t', '--test'): CONTENT, ASSIGN_PAIRS = DRYRUN
        elif k in ('-f', '--full'): CONTENT, ASSIGN_PAIRS = FULL_CONTENT
        elif k in ('-c', '--content'): CONTENT = v
        elif k in ('-u', '--unpaired'): ASSIGN_PAIRS = False
        elif k in ('-p', '--paired'): ASSIGN_PAIRS = True
        elif k in ('-d', '--debug'): DEBUG = True
        elif k in ('-r', '--release'): DEBUG = False
        elif k in ('-n', '--no-client'): CLIENT = False
        elif k in ('-w', '--with-client'): CLIENT = True
        elif k in ('-g', '--group'): GROUP = v
        elif k in ('-h', '--help'):
            print('state:\n  ', state_format % (CLIENT, DEBUG, CONTENT, ASSIGN_PAIRS, EMAIL, GROUP))
            print('protip:\n  use -h as last arg to inspect state w/out actually running anything')
            print('  CLIENT := calls SecretSanta()')
            print('  DEBUG := print statements, wont call send()')
            print('  CONTENT := loaded content for email body')
            print('  PAIRED := match content on %s from rolls')
            print('  GROUP := the specified list of participants')
            print()
            print('usage:')
            for i in usage: print('  -%s, --%s' % (i[0], i))
            print()
            print('.santa/notes')
            exit(0)

    print(state_format % (CLIENT, DEBUG, CONTENT, ASSIGN_PAIRS, EMAIL, GROUP))

    for k,v in opts:
        if k in ('-s', '--send'):
            CLIENT = False
            send(v, 'A Test %s' % year(), get_content())

    if CLIENT: SecretSanta()

    print( '##--DONE--##' )

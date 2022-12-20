#!/usr/bin/env python3

import base64
import email
import imaplib
import json
import sqlite3
import urllib
import yagmail

from contextlib import closing
from datetime import datetime
from getopt import getopt
from os import getenv, rename, remove
from pprint import pprint
from random import shuffle
from typing import Dict, List, Tuple
from sys import argv

DRYRUN = (getenv('SANTA_TEST_CONTENT'), False)
FULL_CONTENT = (getenv('SANTA_CONTENT'), True)

CLIENT = True
DEBUG = True
CONTENT, ASSIGN_PAIRS = DRYRUN

GROUP = getenv('SANTA_GROUP')
EMAIL = getenv('SANTA_EMAIL')
OAUTH_PATH = getenv('SANTA_OAUTH') if getenv('SANTA_OAUTH') else '.santa/oauth2_cred.json'
DB_PATH = getenv('SANTA_DB_PATH') if getenv('SANTA_DB_PATH') else '.santa/santaslist.db'

class SecretSanta:
    db = sqlite3.connect(DB_PATH)

    participants: Dict[str, str] = {}
    pairs: List[Tuple[str, str]] = []

    def __init__(self):
        with closing(self.db.cursor()) as c:
            c.execute(f'SELECT * FROM {GROUP}')
            # dict of name -> email
            self.participants = dict(c.fetchall())

        self.roll()
        self.send_pairs()

    def roll(self) -> None:
        names = [x for x in self.participants]
        pairs: List[Tuple[str, str]] = []
        while not len(pairs) is len(names):
            del pairs[:] # clear list
            b = names.copy() # deep copy
            for x in names:
                shuffle(b) # shuffle b
                if not x is b[-1]:
                    pairs.append((x, b.pop())) # remove item in b taken

        self.pairs = pairs

        if DEBUG: print(f"{self.pairs}\n")

    def send_pairs(self) -> None:
        for pair in self.pairs:
            to = self.participants[pair[0]]      # get left email
            subject = f"FROM SANTA!! {year()}"   # prevent weird reply nonsense
            body = get_pair(get_content(), pair) # if ASSIGN_PAIRS get_content() % pair

            send(to, subject, body)

def year() -> int:
    return datetime.now().date().year

def get_content() -> str:
    c = ''
    with open(CONTENT) as f:
        for line in f: c += line
    return c

def get_pair(c: str, p: str) -> str:
    return c % p if ASSIGN_PAIRS else c

def send(to: str, subj: str, body: str, preview=-1) -> None:
    if DEBUG: print(to, subj, body[0:preview])
    else:
        yagmail.SMTP( EMAIL, oauth2_file=OAUTH_PATH )\
               .send( to, subj, body )
        print( 'SENT to ', to )

# TODO figure out how to replace this, it will be depricated in 2023
GOOGLE_OAUTH_REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
GOOGLE_ACCOUNTS_BASE_URL = 'https://accounts.google.com'
class OAUTH2:
    secrets = {}
    def __init__(self):
        with open(OAUTH_PATH, 'r') as fp:
            self.secrets: Dict = json.load(fp)

    @staticmethod
    def url_unescape(text: str) -> str:
        return urllib.parse.unquote(text)

    @staticmethod
    def url_escape(text: str) -> str:
        return urllib.parse.quote(text, safe='~-._')

    @staticmethod
    def url_format_params(params: Dict) -> str:
        param_fragments = []
        for param in sorted(params.items(), key=lambda x: x[0]):
            key = param[0]
            val = OAUTH2.url_escape(param[1])
            param_fragments.append(f'{key}={val}')
        return '&'.join(param_fragments)

    @staticmethod
    def to_request(command: str) -> str:
        return f'{GOOGLE_ACCOUNTS_BASE_URL}/{command}'

    @staticmethod
    def generate_oauth2_string(access_token: str, as_base64=False) -> str:
        auth_string = f'user={EMAIL}\1auth=Bearer {access_token}\1\1'
        if as_base64:
            auth_string = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
        return auth_string

    def generate_permission_url(self, scope='https://mail.google.com/') -> str:
        params = {}
        params['client_id'] = self.secrets['google_client_id']
        params['redirect_uri'] = GOOGLE_OAUTH_REDIRECT_URI
        params['scope'] = scope
        params['response_type'] = 'code'
        params['ack_oob_shutdown'] = '2022-10-03'
        request_url = OAUTH2.to_request('o/oauth2/auth')
        request_params = OAUTH2.url_format_params(params)
        return f'{request_url}?{request_params}'

    def call_authorize_tokens(self, authorization_code: str) -> Dict:
        params = {}
        params['client_id'] = self.secrets['google_client_id']
        params['client_secret'] = self.secrets['google_client_secret']
        params['code'] = authorization_code
        params['redirect_uri'] = GOOGLE_OAUTH_REDIRECT_URI
        params['grant_type'] = 'authorization_code'
        request_url = self.to_request('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode('UTF-8')
        return json.loads(response)

    def get_authorization(self) -> Tuple[str, str, str]:
        scope = "https://mail.google.com/"
        print('Navigate to the following URL to auth:', self.generate_permission_url(scope))
        authorization_code = input('Enter verification code: ')
        response = self.call_authorize_tokens(authorization_code)
        return response['refresh_token'], response['access_token'], response['expires_in']

    def call_refresh_token(self) -> Dict:
        params = {}
        params['client_id'] = self.secrets['google_client_id']
        params['client_secret'] = self.secrets['google_client_secret']
        params['refresh_token'] = self.secrets['google_refresh_token']
        params['grant_type'] = 'refresh_token'
        request_url = self.to_request('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode('UTF-8')
        return json.loads(response)

    def refresh_authorization(self) -> Tuple[str, str]:
        response = self.call_refresh_token()
        return response['access_token'], response['expires_in']

    def get_token_secrets(self):
        refresh_token, _, _ = self.get_authorization()

        print('Set the following as your GOOGLE_REFRESH_TOKEN:', refresh_token)
        self.secrets['google_refresh_token'] = refresh_token

        input('press enter to confirm delete cred backup')
        remove(OAUTH_PATH + '.old')
        rename(OAUTH_PATH, OAUTH_PATH + '.old')

        with open(OAUTH_PATH, 'w') as fp:
            json.dump(self.secrets, fp)

class IMTP:
    def __init__(self, oauth: OAUTH2):
        self.oauth = oauth

    @staticmethod
    def pprint(raw_email: bytes):
        fields = IMTP.extract(raw_email)
        pprint(fields)

    @staticmethod
    def extract_field(raw_field: str) -> Tuple[str, str]:
        split = raw_field.split(': ')
        key = split[0].strip()
        value = ''.join(split[1:]).strip()
        return key, value

    @staticmethod
    def extract(raw_email: bytes) -> Dict:
        fields = raw_email.decode('utf-8')
        fields = fields.split('\r\n')
        fields = filter(lambda x: ': ' in x, fields)
        fields = map(IMTP.extract_field, fields)
        fields = dict(fields)
        return fields

    @staticmethod
    def parse_email(raw_email: bytes) -> str:
        parsed_email = email.message_from_bytes(raw_email)
        encoded = parsed_email.get_payload()[0]             # only 1 payload in list (probably?)
        encoded = encoded.as_string().split('\n')           # filter out newlines
        encoded = filter(lambda x: not ': '  in x, encoded) # filter out headers
        encoded = filter(lambda x: not '--' in x, encoded)  # filter out partitions (this is awkward i should really make sure the orders is right)
        encoded = ''.join(encoded)                          # join to create complete base64 string
        decoded = base64.b64decode(encoded).decode("utf-8") # back to utf-8 string
        return decoded

    @staticmethod
    def fetch(imap_conn: imaplib.IMAP4_SSL, needle: str, N=1) -> List[Tuple[Dict, str]]:
        _, data = imap_conn.search(None, needle)
        matches = data[0].split()[-N:][::-1] # grab the latest email meeting the criterion
        results = []
        for match in matches:
            _, data = imap_conn.fetch(match, '(RFC822)')
            raw_email = data[0][1]
            parsed = IMTP.parse_email(raw_email)
            fields = IMTP.extract(raw_email)
            results.append((fields, parsed))

        return results

    def search(self, to: str, subject:str = None) -> List[Tuple[Dict, str]]:
        access_token, _ = self.oauth.refresh_authorization()
        auth_string = self.oauth.generate_oauth2_string(access_token)

        imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
        # imap_conn.debug = 4
        imap_conn.authenticate('XOAUTH2', lambda x: auth_string)

        imap_conn.select('"[Gmail]/Sent Mail"')
        maybe_subject = f' SUBJECT "{subject}"' if subject else ''
        results = self.fetch(imap_conn, f'(TO "{to}"{maybe_subject})', 1)

        imap_conn.close()
        imap_conn.logout()

        return results

def print_state():
    print(f'{DEBUG=} {ASSIGN_PAIRS=} {CONTENT=} {EMAIL=} {GROUP=}\n')

def print_help(usage: List[str]):
    print('state:\n  ', end='')
    print_state()
    print('protip:\n  use -h as last arg to inspect state w/out actually running anything')
    print('  DEBUG := print statements, wont call send()')
    print('  PAIRED := match content on %s from rolls')
    print('  CONTENT := loaded content for email body, template containing 2 %s, from ENV SANTA_CONTENT | SANTA_TEST_CONTENT')
    print('  EMAIL := the gmail, from ENV SANTA_EMAIL')
    print('  GROUP := the specified list of participants, from ENV SANTA_GROUP')
    print()
    print('usage:')
    for flag in usage: print(f'  --{flag}')
    print()
    print('source .santa/notes')
    exit(0)

if __name__ == '__main__':

    usage = ['help', 'get-token-secrets', 'dryrun', 'full', 'release', 'send=', 'resend=']
    opts, _ = getopt(argv[1:], 'hgdfrs:x:', usage)
    for k, v in opts:
        if k in ('-f', '--full'): CONTENT, ASSIGN_PAIRS = FULL_CONTENT
        elif k in ('-d', '--dryrun'): CONTENT, ASSIGN_PAIRS = DRYRUN
        elif k in ('-r', '--release'): DEBUG = False
        elif k in ('-h', '--help'): print_help(usage)

    if len(argv) == 1: print_help(usage)
    print_state()

    # complex operations
    for k, v in opts:
        if k in ('-s', '--send'):
            send(v, f'A Test {year()}', get_content())
            exit(0)
        elif k in ('-x', '--resend'):
            # search the sent inbox for <email> | "<email>,<subject>"
            args = v.split(',')
            inbox = IMTP(OAUTH2())
            results = inbox.search(args[0], args[1]) if len(args) == 2 else inbox.search(v)

            for fields, body in results:
                to    = fields['To']
                subj  = fields['Subject'] + f' -- Second Notice for {year()}'
                shame = 'It seems like someone failed to get the memo :/<br><br>'
                body  = shame + body
                preview  = len(shame) + 40 # get a nice window that doesnt reveal too much
                send(to, subj, body, preview=preview)

            exit(0)
        elif k in ('-g', '--get-token-secrets'):
            # Generate and authorize OAuth2 secrets
            # results will be dumped to OAUTH_PATH env
            OAUTH2().get_token_secrets()
            exit(0)

    SecretSanta()

    print( '##--DONE--##' )

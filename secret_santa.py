#!/usr/bin/env python3

import yagmail
from imbox import Imbox

from random import shuffle
from time import sleep
from sys import argv
import sqlite3
from contextlib import closing
from getopt import getopt

DRYRUN = ('test.txt', False)
FULL_CONTENT = ('content.txt', True)

CLIENT = True
DEBUG = True
CONTENT, ASSIGN_PAIRS = DRYRUN

class SecretSanta:
    db = sqlite3.connect('santaslist.db')

    groups = dict()
    reroll = dict()
    pairs = []
    passwd = '1234'
    sender = 'schultechristmas@gmail.com'
    oauth = '~/.santa/oauth2_cred.json'
    
    def __init__(self, sender=(None,None), rate=None):
        if not sender == (None, None):
            self.sender = sender[0]
            self.oauth = sender[1]

        ## use sqlite
        grps = []
        with closing(self.db.cursor()) as c:
            c.execute('SELECT * FROM grps')

            for grp in c:
                grps.append( grp[0] )

            for grp in grps:
                c.execute('SELECT * FROM %s' % (grp,))
                self.groups[grp] = dict( c.fetchall() )

        # print( self.groups )

        self.reroll[grp] = dict()

        # TODO for each grp if no pairs DB roll
        self.roll(grp)
        
        # TODO loop through inbox
        # if rate: self.check_inbox( r=rate )
        # else: self.check_inbox()

        
    def roll(self, grp):
        names = [x for x in self.groups[grp]]
        pairs = []
        while not len(pairs) is len(names):
            del pairs[:] # clear list
            b = names.copy() # deep copy
            for x in names:
                shuffle(b) # shuffle b
                if not x is b[-1]:
                    pairs.append((x,b.pop())) # remove item in b taken

        self.pairs = pairs
        # TODO save pairs in DB
        if DEBUG: print("%s\n" % self.pairs)

        self.roll_send(get_content(), grp)

    def roll_send(self, content, grp):
        for pair in self.pairs:
            # print( '%s has %s' % pair )

            to = self.groups[grp][pair[0]]
            subject = "FROM SANTA!!"
            body =  get_pair(content, pair)

            if DEBUG: print(to, subject, body)
            else: self.send(to, subject, body)

    def send(self, to, subj, body): 
        yagmail.SMTP( self.sender, oauth2_file=self.oauth )\
               .send( to, subj, body )

        print( 'SENT to ', to )

    def check_inbox(self, r=30):
        import keyring

        while True:
            with Imbox('imap.gmail.com',
                username='schultechristmas@gmail.com',
                password= keyring.get_password( 'system', 'schultechristmas' ),
                ssl=True,
                ssl_context=None,
                starttls=False) as imbox:

                unread_msgs = imbox.messages(unread=True)

                for uid, message in unread_msgs:
                    imbox.mark_seen(uid)

                    if '[CMD]' in message.subject:
                        self.cmd(message)

                    # make sure the sender is in the group
                    # make sure grp is in groups
                    # strip Re from subject field
                    try:
                        if 'Re' in message.subject.split(' ')[0]: 
                            del message.subject.split(' ')[0]
                        grp = message.subject.split(' ')[0][1:-1]
                    except IndexError:
                        grp = ''

                    try:
                        msg_type = message.subject.split(' ')[1][1:-1]
                    except IndexError:
                        msg_type = ''

                    try:
                        option = message.subject.split(' ')[2][1:-1]
                    except IndexError:
                        option = ''

                    if msg_type == 'CRT' and option == self.passwd:
                        self.crt(message, grp)

                    ## All other cmds require valid grp
                    if not grp in self.groups: continue
                    if not message.sent_from[0]['email'] in self.groups[grp].values(): continue

                    if 'BCAST' in message.subject:
                        self.bcst(message, grp)

                    if msg_type == 'WSPR' and option in '[From] Secret Santa]':
                        self.wspr_to(message, grp)

                    if msg_type == 'WSPR' and option in '[To] Secret Santa]':
                        self.wspr_from(message, grp)

                    if msg_type == 'ADD' and option == self.passwd:
                        self.add(message, grp)

                    if msg_type == 'RM':
                        self.rm(message, grp)

                    if msg_type == 'PWROLL' and option == 'Please_be_careful_1234567890' + self.passwd:
                        self.roll(grp)

                    if msg_type == 'ROLL':
                        self.reroll[grp].update( message.sent_from[0]['name'] )
                        # 2/3 majority
                        if len(self.reroll[grp]) > 2 * len(self.groups[grp]) / 3:
                            self.roll(grp)

            sleep(r) # sleep for 30s to not spam email

    def bcst(self, message, grp):
        names = [x for x in self.groups[grp]]
        for name in names:
            # print(n[x], '[Alert] Secret Santa', 'demo') #message.body['plain']
            sender = message.sent_from[0]['email']
            name = list(self.groups[grp].keys())[list(self.groups[grp].values()).index( sender )]

            to = self.groups[grp][name]
            subj = '[Alert] Secret Santa'
            body = '<b>Broadcast Message from %s,</b>\n\n%s' % ( name, message.body['plain'] )

            self.send( to, subj, body )

    def cmd(self, message):
        # print(message.body['plain'])
        to = message.sent_from[0]['email']
        subj = '[Auto Reply] [Commands]'
        body = 'Commands are sent as the <b>email subject</b>.' + \
                ' Please use form: [GROUP] [MSG_TYPE] [OPTIONS]\n\n' + \
                'GROUP = name of the group you are a member of\n' + \
                'MSG_TYPE = user command to the auto mailer\n' + \
                'OPTIONS = additional information -- only required for [WSPR]\n\n' + \
                'Commands [MSG_TYPE]:\n' + \
                ' &nbsp; [WSPR]: send message to Secret Santa' + \
                ', they can reply back (ANONOMOUSLY)\n' + \
                ' &nbsp; &nbsp; - [OPTIONS] = [From] : sends message to person recieving gift from you\n' + \
                ' &nbsp; &nbsp; - [OPTIONS] = [To]   : sends message to person giving you a gift\n' + \
                ' &nbsp; &nbsp; &nbsp; - EX = [GROUP] [WSPR] [From]\n' + \
                ' &nbsp; &nbsp; &nbsp; - EX = [GROUP] [WSPR] [To]\n' + \
                ' &nbsp; [BCAST]: send a message to all emails in the group\n\n' + \
                ' <i>Extended Commands</i>\n' + \
                ' &nbsp; [CMD]: returns a list of commands\n' + \
                ' &nbsp; [CRT]: creates a new group\n' + \
                ' &nbsp; [ADD]: adds email to group\n' + \
                ' &nbsp; [RM]: remove email from group\n'

        self.send( to, subj, body )

    def crt(self, message, grp):
        with closing(self.db.cursor()) as c:
            # Add table {GRP}
            c.execute('CREATE TABLE %s (name text, email text)' % 
                (grp,) )

            # Add entry to {GRP}
            c.execute('INSERT INTO %s VALUES (?, ?)' % grp,
                (message.sent_from[0]['name'], message.sent_from[0]['email']) )

            # Add entry to GRPS
            c.execute('INSERT INTO grps VALUES (?)', (grp,) )

        self.groups[grp] = dict()
        self.groups[grp][message.sent_from[0]['name']] = message.sent_from[0]['email']
        self.reroll[grp] = set()

        # print(self.groups[grp])
        # consider to send confirm email
        print('CREATED', grp)

    def add(self, message, grp):
        with closing(self.db.cursor()) as c:
            # Add entry to {GRP}
            c.execute('INSERT INTO %s VALUES (?, ?)' % grp,
                (message.sent_from[0]['name'], message.sent_from[0]['email']) )

        self.groups[grp][message.sent_from[0]['name']] = message.sent_from[0]['email']

        # print(self.groups)
        # confirm email
        print('ADDED')

    def rm(self, message, grp):
        with closing(self.db.cursor()) as c:
            # rm entry from {GRP}
            c.execute('DELETE FROM %s WHERE email=?' % grp,
                (message.sent_from[0]['email'],) )
        

        self.groups[grp].pop( message.sent_from[0]['name'], None )
        self.reroll[grp].pop( message.sent_from[0]['name'], None )
        # print(self.groups)
        # confirm email

        print('REMOVED')
        if not self.groups[grp]:
            self.groups.pop(grp)
            self.reroll.pop(grp)

            with closing(self.db.cursor()) as c:
                # Rm entry from GRPS ( if necessary )
                c.execute('DELETE FROM grps VALUES (?)', (grp,) )

            print('%s deleted' % grp)

    def wspr_to(self, message, grp):
        sender = message.sent_from[0]['email']
        name = list(self.groups[grp].keys())[list(self.groups[grp].values()).index( sender )]

        whisper_dst = self.groups[grp][ self.pairs[name] ]
        subj = '[%s] [WSPR] [To] Secret Santa' % (grp,)
        # look for Sent -> delete everything after that
        body = message.body['plain'].split("\nSent from")[0] ## strip this of end stuff -- harder to weed out sender

        self.send( whisper_dst, subj, body )
        
    def wspr_from(self, message, grp):
        pairs_dict = dict(self.pairs)
        sender = message.sent_from[0]['email'] # replys back

        name = list(self.groups[grp].keys())[list(self.groups[grp].values()).index( sender )]
        whisper_name = list(pairs_dict.keys())[list(pairs_dict.values()).index( name )]

        whisper_email =  self.groups[grp][whisper_name]
        subj = '[%s] [WSPR] [From] Secret Santa' % (grp,)
        # look for Sent -> delete everything after that
        body = message.body['plain'].split("\nSent from")[0] ## strip this of end stuff -- harder to weed out sender

        self.send( whisper_email, subj, body )

def get_content():
    c = ''
    with open(CONTENT) as f:
        for line in f: c += line
    return c

def get_pair(c, p):
    return c % p if ASSIGN_PAIRS else c

def send(email):
    if DEBUG: print(get_content())
    yagmail.SMTP('schultechristmas@gmail.com', oauth2_file='~/.santa/oauth2_cred.json')\
           .send( email, 'A Test', get_content() )


if __name__ == '__main__':

    usage = ['help', 'with-client', 'no-client', 'test', 'full', 'debug', 'release', 'send=', 'content=', 'paired', 'unpaired']
    opts, _ = getopt(argv[1:], 'hwntfdrs:c:pu', usage)
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
        elif k in ('-h', '--help'):
            print('state: CLIENT(%s) DEBUG(%s) CONTENT(%s) PAIRED(%s)\n' % (CLIENT, DEBUG, CONTENT, ASSIGN_PAIRS))
            print('protip:\n  use -h as last arg to inspect state w/out actually running anything')
            print('  CLIENT := calls SecretSanta()')
            print('  DEBUG := print statements, wont call send()')
            print('  CONTENT := loaded content for email body')
            print('  PAIRED := match content on %s from rolls')
            print()
            print('usage:')
            for i in usage: print('  -%s, --%s' % (i[0], i))
            exit(0)

    print('CLIENT(%s) DEBUG(%s) CONTENT(%s) PAIRED(%s)\n' % (CLIENT, DEBUG, CONTENT, ASSIGN_PAIRS))

    for k,v in opts:
        if k in ('-s', '--send'):
            CLIENT = False
            send(v)

    if CLIENT: SecretSanta()

    print( '##--DONE--##' )

## TODO
#
# Groups -- use [GRP_NM] [MSG_TYPE] [OPTIONS]
#        -- groups = { GRP_NM, {(name,email)} }
#
# Create group
#        -- GRP_NM = 'new name'
#        -- MSG_TYPE = 'CRT'
#        -- OPTIONS = 'password'
#            -- optional
#
#        -- groups[GRP_NM] = dict()
#        -- groups[GRP_NM][message.sent_from[0]['name']] = message.sent_from[0]['email']
#
# Add to group
#        -- GRP_NM = <group>
#        -- MSG_TYPE = 'ADD'
#        -- OPTIONS = 'password'
#        -- groups[GRP_NM][message.sent_from[0]['name']] = message.sent_from[0]['email']
# 
# Remove from group
#        -- GRP_NM = <group>
#        -- MSG_TYPE = 'RM'
#        -- OPTIONS = not used
#
#        -- if all join from email
#           -- name = message.sent_from[0]['name']
#        -- else
#           -- name = { (email, name) }  -- the reverse of emails
#
#        -- groups[GRP_NM].pop( name, None )
#
# Request re-roll (NOT ENCLUDED)
#        -- REQUIRES a class to keep persistant collections
#        -- GRP_NM = <group>
#        -- MSG_TYPE = 'ROLL'
#        -- SUBJECT = not used
#
#        -- roll_count += 1
#        -- if roll_count > 2 * len(groups[GRP_NM]) / 3
#            -- BCAST "Reroll has a 2/3 vote -- new pairs to be assigned"
#            -- reroll()
#
# SQLITE
#
#   GRPS                            {GRP}
# - list all groups               - a table per GRP in GRPS
#                                 - NAME, EMAIL
#


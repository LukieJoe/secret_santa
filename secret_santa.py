#!/usr/bin/env python3

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


import yagmail
from imbox import Imbox

from random import shuffle
from time import sleep
import sqlite3
from contextlib import closing

class SecretSanta:
    db = sqlite3.connect('santaslist.db')

    groups = dict()
    reroll = dict()
    pairs = []
    passwd = '1234'
    sender = 'schultechristmas@gmail.com'
    oauth = '~/.santa/oauth2_cred.json'
    
    def __init__(self, sender=(None,None), rate=None):
        if sender:
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

        print( self.groups )

        self.reroll[grp] = dict()
        self.roll(grp)
        
        if rate: self.check_inbox(rate)
        else: self.check_inbox()

        
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
        # print(self.pairs)

        # format for the message
        content = "Dear %s,\n\nThis has been a very busy year for" + \
                " me and I need YOUR help to save Christmas." + \
                " Please get a super special gift for <b>%s" + \
                "</b>. You're filling in for me so please," + \
                " keep this a secret!! Have a Merry Schulte" + \
                " Christmas.\n\nAlways yours,\nSanta Claus\n"

        self.roll_send(content, grp)

    def roll_send(self, content, grp):
        for pair in self.pairs:
            # print( '%s has %s' % pair )

            to = self.groups[grp][pair[0]]
            subject = "FROM SANTA!!"
            body =  content % pair

            # print(to, subject, body)

            # ## Test 
            # print(to + "\nSecret Santa\n" + "Dear " + pair[0] +
            #         ",\n\nThis is a test of the Emergency" +
            #         " Santa Help Network.\n<b>Action Required.</b>" +
            #         " Please reply ASAP!\n\nSanta's NO.1 elf,\nBuddy")

            # ## Deploy with this
            self.send(to, subject, body)

            # ## Test with this
            # self.send(to, "Secret Santa", "Dear " + x[0] +
            #           ",\n\nThis is a test of the emergency" +
            #           " Santa Help Network.\n<b>Action Required.</b>" +
            #           " Please reply ASAP!\n\nSanta's NO.1 elf,\nBuddy")
    
    def check_inbox(self, rate=30):
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

            sleep(rate) # sleep for 30s to not spam email

    def send(self, to, subj, body):
        print( 'SENT\n', to, subj, body )
        # yagmail.SMTP( self.sender, oauth2_file=self.oauth)\
        #         .send( to, subj, body )

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
        body = 'Commands are sent as the email subject.' + \
                ' Please use form: [GRP_NM] [MSG_TYPE] [OPTIONS]\n\n' + \
                'GRP_NM = name of the group you are a member of\n' + \
                'MSG_TYPE = user command to the auto mailer\n' + \
                'OPTIONS = additional information -- password if required\n\n' + \
                'Commands (MSG_TYPE):\n' + \
                '\t[CMD]: returns a list of commands\n' + \
                '\t[CRT]: creates a new group\n' + \
                '\t[ADD]: adds email to group\n' + \
                '\t[RM]: remove email from group\n' + \
                '\t[WSPR]: send message to Secret Santa' + \
                ', they can reply back (ANONOMOUSLY)\n' + \
                '\t  - OPTION = From: sends message to person recieving gift from you\n' + \
                '\t  - OPTION = To: sends message to person giving you a gift\n' + \
                '\t[BCST]: send a message to all emails in the group\n'

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
        body = message.body['plain'] ## strip this of end stuff -- harder to weed out sender

        self.send( whisper_dst, subj, body )
        
    def wspr_from(self, message, grp):
        pairs_dict = dict(self.pairs)
        sender = message.sent_from[0]['email'] # replys back

        name = list(self.groups[grp].keys())[list(self.groups[grp].values()).index( sender )]
        whisper_name = list(pairs_dict.keys())[list(pairs_dict.values()).index( name )]

        whisper_email =  self.groups[grp][whisper_name]
        subj = '[%s] [WSPR] [From] Secret Santa' % (grp,)
        # look for Sent -> delete everything after that
        body = message.body['plain'] ## strip this of end stuff -- harder to weed out sender

        self.send( whisper_email, subj, body )
    
if __name__ == '__main__':
    ## fill this from subscribers list ??
    # emails = dict([('Luke Joseph', 'lukepaltzer@gmail.com'),
                    # ('Luke', 'landers345@gmail.com')])
                    # ('Dev','devpaltzer@gmail.com'),
                    # ('Sean', 'seanpaltzer@gmail.com'),
                    # ('Martha', 'mspaltzer@gmail.com'),
                    # ('Sarah', 'svincent@gmail.com'),
                    # ('Mary', 'maryv0444@gmail.com'),
                    # ('Sidney', 'sidvinc02@gmail.com'),
                    # ('Travis', 'tvincent11@gmail.com'),
                    # ('Cayla', 'cwolfe@hotmail.com'),
                    # ('Holli', 'hollimorris18@gmail.com'),
                    # ('Julie', 'jschulte13@yahoo.com'),
                    # ('Luke Leon', 'luke_leon@yahoo.com')])

    ## Create a secret santa with the list of emails you want to track
    ## Default constructor will still allow to roll
    #    Have all members send email to Emailer
    #    Then send the roll cmd

    s = SecretSanta( rate=0 )

'''
    ## take only first values from n
    names = [name for name in emails]

    # finds pairs such no (a,a)
    pairs = []
    while not len(pairs) is len(names):
        del pairs[:] # clear list
        b = names.copy() # deep copy
        for x in names:
            shuffle(b) # shuffle b
            if not x is b[-1]:
                pairs.append((x,b.pop())) # remove item in b taken

    ## view pairs
    print(pairs)

    # format for the message
    content = "Dear %s,\n\nThis has been a very busy year for" + \
              " me and I need YOUR help to save Christmas." + \
              " Please get a super special gift for <b>%s" + \
              "</b>. You are filling in for me so please," + \
              " keep this a secret!! Have a Merry Schulte" + \
              " Christmas.\n\nAlways yours,\nSanta Claus\n"

    # use name to lookup email
    # name, name
    # email[name], name

    for pair in pairs:
        # print( '%s has %s' % pair )

        to = emails[pair[0]]
        subject = "FROM SANTA!!"
        body =  content % pair

        # ## Test 
        # print(to + "\nSecret Santa\n" + "Dear " + pair[0] +
        #         ",\n\nThis is a test of the Emergency" +
        #         " Santa Help Network.\n<b>Action Required.</b>" +
        #         " Please reply ASAP!\n\nSanta's NO.1 elf,\nBuddy")

        # ## Deploy with this
        # yagmail.SMTP('schultechristmas@gmail.com',
        #             oauth2_file='~/.santa/oauth2_cred.json')\
        #              .send(to, subject, body)

        # ## Test with this
        # yagmail.SMTP('schultechristmas@gmail.com',
        #               oauth2_file='~/.santa/oauth2_cred.json')\
        #                 .send(to, "Secret Santa", "Dear " + x[0] +
        #                        ",\n\nThis is a test of the emergency" +
        #                        " Santa Help Network.\n<b>Action Required.</b>" +
        #                        " Please reply ASAP!\n\nSanta's NO.1 elf,\nBuddy")

    ## BCAST
    # if message.subject == 'BCAST' + key:
    # for x in a:
    #     print(n[x], '[Alert] Secret Santa', 'demo') #message.body['plain']

    ## WHISPER
    pairs_dict = dict(pairs)
    # print(pairs_dict)

    ## TO
    # get name from sender email
    # get email from name

    ## BACK
    # get name from email
    # find the name from pair (_,x)
    # use x to find _
    # find email from _

    # remove 'not' to use
    # do error checking to prevent crashes (element not in list)
    # move keyring to os.enviorn['SANTA_PASS'] ??
    import keyring

    while not True:
        with Imbox('imap.gmail.com',
            username='schultechristmas@gmail.com',
            password= keyring.get_password( 'system', 'schultechristmas' ),
            ssl=True,
            ssl_context=None,
            starttls=False) as imbox:

            unread_msgs = imbox.messages(unread=True)

            for uid, message in unread_msgs:
                imbox.mark_seen(uid)

                if message.subject == 'test':
                    # print(message.body['plain'])
                    to = message.sent_from[0]['email']
                    subj = '[Auto Reply]'
                    body = 'You sent\n\"\n%s\n\"' % message.body['plain']
                    yagmail.SMTP('schultechristmas@gmail.com',
                            oauth2_file='~/.santa/oauth2_cred.json')\
                            .send( to, subj, body )

                # make sure the sender is in the group
                # pass vs break ??
                if not message.sent_from[0]['email'] in emails.values(): pass

                if message.subject == 'BCAST !!':
                    for name in names:
                        # print(n[x], '[Alert] Secret Santa', 'demo') #message.body['plain']
                        sender = message.sent_from[0]['email']
                        name = list(emails.keys())[list(emails.values()).index( sender )]
                        to = emails[name]
                        subj = '[Alert] Secret Santa'
                        body = '<b>Broadcast Message from %s,</b>\n\n%s' % ( name, message.body['plain'] )
                        yagmail.SMTP('schultechristmas@gmail.com',
                                oauth2_file='~/.santa/oauth2_cred.json')\
                                .send( to, subj, body )

                if message.subject == 'WHISPER' or message.subject in 'Re: [Whisper From] Secret Santa':
                    sender = message.sent_from[0]['email']
                    name = list(emails.keys())[list(emails.values()).index( sender )]
                    whisper_dst = emails[ pairs[name] ]
                    subj = '[Whisper To] Secret Santa'
                    body = message.body['plain']
                    yagmail.SMTP('schultechristmas@gmail.com',
                            oauth2_file='~/.santa/oauth2_cred.json')\
                            .send( whisper_dst, subj, body )

                if message.subject in 'Re: [Whisper To] Secret Santa':
                    sender = message.sent_from[0]['email'] # replys back
                    name = list(emails.keys())[list(emails.values()).index( sender )]
                    whisper_name = list(pairs_dict.keys())[list(pairs_dict.values()).index( name )]
                    whisper_email =  emails[whisper_name]
                    subj = '[Whisper From] Secret Santa'
                    body = message.body['plain']
                    yagmail.SMTP('schultechristmas@gmail.com',
                            oauth2_file='~/.santa/oauth2_cred.json')\
                            .send( whisper_email, subj, body )

        sleep(30) # sleep for 30s to not spam email

    ## general format
    # yagmail.SMTP('schultechristmas@gmail.com', oauth2_file='~/.santa/oauth2_cred.json').send(TO, SUBJECT, BODY)
'''
#!/usr/bin/env python3

import sqlite3
from contextlib import closing
from sys import argv
from os import getenv

print("%s usage:\n  ./ -- print db\n  ./ <name> -- delete where name (case sensitive)\n  ./ <name> <email> -- insert name,email into db\n" % argv[0])

DB_PATH = getenv('SANTA_DB_PATH') if getenv('SANTA_DB_PATH') else '.santa/santaslist.db'

with sqlite3.connect(DB_PATH) as db:
    with closing(db.cursor()) as c:
        #c.execute('''CREATE TABLE grps
        #         (grp text)''')

        #c.execute('''CREATE TABLE SC
        #         (name text, email text)''')

        if len(argv) == 3:
            stmt = """INSERT INTO SC VALUES('%s', '%s')""" % (argv[1], argv[2])
            print(stmt)
            c.execute(stmt)

        if len(argv) == 2:
            c.execute("""DELETE FROM SC WHERE name = '%s'""" % (argv[1],))

        #c.execute("""INSERT INTO grps VALUES (?)""", ('SC',))

        c.execute('''SELECT * FROM grps''')

        #print( c.fetchall()[0] )

        c.execute('SELECT * FROM %s' % c.fetchall()[0][0] )

        tmp = c.fetchall()
        print( "total: %s\n" % len(tmp) )
        for i in tmp: print(i)

        # t = ("SC", )
        # c.execute(' SELECT * FROM %s ' % t )

        # print ( c.fetchall() )

#!/usr/bin/env python3

import sqlite3
from contextlib import closing
from sys import argv
from os import getenv

print("""\
%s usage:
  ./ -- print db
  ./ <name> -- delete where name (case sensitive)
  ./ <name> <email> -- insert name,email into db
  ./ create <table name> -- create a table and add keys to groups table
""" % argv[0])

DB_GROUP = getenv('SANTA_GROUP')
DB_PATH = getenv('SANTA_DB_PATH') if getenv('SANTA_DB_PATH') else '.santa/santaslist.db'

with sqlite3.connect(DB_PATH) as db:
    with closing(db.cursor()) as c:
        #c.execute('''CREATE TABLE grps (grp text)''')

        if len(argv) == 3:
            if argv[1] == 'create':
                c.execute('''CREATE TABLE %s (name text, email text)''' % (argv[2],))
                c.execute("""INSERT INTO grps VALUES (?)""", (argv[2],))
            else:
                stmt = """INSERT INTO %s VALUES('%s', '%s')""" % (DB_GROUP, argv[1], argv[2])
                print(stmt)
                c.execute(stmt)

        if len(argv) == 2:
            c.execute("""DELETE FROM %s WHERE name = '%s'""" % (DB_GROUP, argv[1],))

        c.execute('''SELECT * FROM grps''')

        for grp in c.fetchall():
            print('group: %s' % grp)
            c.execute('SELECT * FROM %s' % grp )

            tmp = c.fetchall()
            print( "total: %s\n" % len(tmp) )
            for i in tmp: print(i)
            print()


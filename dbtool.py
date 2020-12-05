#!/usr/bin/env python3

import sqlite3
from contextlib import closing
from sys import argv

print("%s usage:\n  ./ -- print db\n  ./ <name> -- delete where name (case sensitive)\n  ./ <name> <email> -- insert name,email into db\n" % argv[0])

with sqlite3.connect('santaslist.db') as db:
    with closing(db.cursor()) as c:
        #c.execute('''CREATE TABLE grps
        #         (grp text)''')

        #c.execute('''CREATE TABLE SC
        #         (name text, email text)''')

        #c.execute("""INSERT INTO SC
        #         VALUES ('Luke Joseph', 'lukepaltzer@gmail.com')""")

        '''
        c.execute("""INSERT INTO SC
                VALUES ('Sean', 'seanpaltzer@gmail.com'),
                       ('Martha', 'mspaltzer@gmail.com'),
                       ('Mary', 'maryv0444@gmail.com'),
                       ('Sidney', 'sidvinc02@gmail.com'),
                       ('Holli', 'hollimorris18@gmail.com'),
                       ('Julie', 'jschulte13@yahoo.com'),
                       ('Luke Leon', 'luke_leon@yahoo.com')""")
        '''
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

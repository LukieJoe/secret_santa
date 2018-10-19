#!/usr/bin/env python3

import sqlite3
from contextlib import closing

with sqlite3.connect('santaslist.db') as db:
    with closing(db.cursor()) as c:
        # c.execute('''CREATE TABLE SC
        #          (name text, email text)''')

        # c.execute("""INSERT INTO SC
        #          VALUES ('Luke Joseph', 'lukepaltzer@gmail.com')""")

        # c.execute("""INSERT INTO SC
        #          VALUES ('Luke', 'landers345@gmail.com')""")

        c.execute('''SELECT * FROM grps''')

        print( c.fetchone()[0] )

        t = ("SC", )
        c.execute(' SELECT * FROM %s ' % t )

        print ( c.fetchall() )

total_pages = 3
page =3

for p in range(page-2,page+3):
    if p>=1 and p<=total_pages:
        print(p) 

import sqlite3

# Connecting to sqlite
conn = sqlite3.connect('Database/t2d.db')
 
# cursor object
cursor = conn.cursor()


cursor.execute("""CREATE TABLE updates (
            rs_id VARCHAR(50) NOT NULL,
            last_update VARCHAR(50)
        ); """)
conn.commit()
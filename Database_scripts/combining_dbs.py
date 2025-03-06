import sqlite3
import os

# try:
# connecting to the target database
conn = sqlite3.connect("./Database/t2d_snp_portal.db")
cursor = conn.cursor()

# attaching the source database 
cursor.execute("""ATTACH DATABASE "./Database/stats.db" AS source_db;""")

# fetching all tables from the source database
cursor.execute("SELECT name FROM source_db.sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(tables)

if tables:

    # copying each table from stats.db to t2d.db
    for table in tables:
        table_name = table[0]
        #print(table_name)
        # create table in target_db
        if table_name != "sqlite_sequence":
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM source_db.{table_name}; 
                """)

    # detach the source database
    cursor.execute("DETACH DATABASE source_db;")

    conn.commit()


loc_to_fst = """SELECT chromosome,start_position FROM fst"""
cursor.execute(loc_to_fst)
locs = cursor.fetchall()

for loc in locs:
    chro = loc[0]
    pos = loc[1]
    location = str(chro) + ":" + str(pos)
    cursor.execute("""
            UPDATE fst
            SET GRCh37_loc = ?
            WHERE chromosome = ? AND start_position = ?""", 
            (location, chro, pos))
    conn.commit()

conn.close()

# remove the stats.db
os.remove("./Database/stats.db")
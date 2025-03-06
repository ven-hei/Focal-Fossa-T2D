import sqlite3

# Connecting to sqlite
conn = sqlite3.connect('../Database/t2d_snp_portal.db')
 
# cursor object
cursor = conn.cursor()

cursor.execute("""
        ALTER TABLE indexes
        ADD GRCh37_window VARCHAR(30);""")
conn.commit()

windows = """SELECT chromosome, start_position FROM tajima_d"""
other_info = """SELECT rs_id, chromosome, GRCh37_position FROM indexes"""

cursor.execute(windows)
windows_results = cursor.fetchall()
cursor.execute(other_info)
other_info_results = cursor.fetchall()

for line in other_info_results:
    try:
        pos = line[2]
        residue = pos % 10000
        window = pos - residue
        print(line)
        print(residue)
        print(window)
        cursor.execute("""
            UPDATE indexes
            SET GRCh37_window = ?
            WHERE chromosome = ? AND GRCh37_position = ?""", 
            (window, line[1], pos))
        conn.commit()
    except:
        continue

conn.close()

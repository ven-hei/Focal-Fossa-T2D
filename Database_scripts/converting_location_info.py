import sqlite3
from pyliftover import LiftOver

# Connecting to sqlite
conn = sqlite3.connect('./Database/t2d_snp_portal.db')
 
# cursor object
cursor = conn.cursor()
# select location info from fst table, the position info for hg19
cursor.execute("SELECT chromosome, start_position FROM fst")
hg19_pos = cursor.fetchall()

# remove the old indexes table
cursor.execute("DROP TABLE indexes")
conn.commit()

# create the indexes table
index_table = """CREATE TABLE indexes (
            index_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rs_id VARCHAR(30) NOT NULL,
            chromosome INT,
            GRCh37_position INT,
            GRCh37_loc VARCHAR(50),
            GRCh38_position INT,
            GRCh38_loc VARCHAR(50),
            GRCh37_window INT,
            FOREIGN KEY (rs_id) REFERENCES snp(rs_id),
            FOREIGN KEY (GRCh37_loc) REFERENCES fst(GRCh37_loc),
            FOREIGN KEY (GRCh37_window) REFERENCES tajima_d(start_position)
            ); """

cursor.execute(index_table)
conn.commit()

# go through the list of the fst positions
for pos19 in hg19_pos:
    # try-except to handle the missing values
    try:
        # add chr to the chromosome number for pyliftover
        chro = "chr"+ str(pos19[0])
        start = pos19[1]
        # define which versions of human genome are used
        lo = LiftOver('hg19', 'hg38')
        # run pyliftover whith the positions
        result = lo.convert_coordinate(chro, start)
        # parse the results from pyliftover for the indexes table
        results_chr = str(result[0][0].strip().split("chr")[1])
        results_old = str(start)
        results_new = str(result[0][1])
        # to connect to tajima_d table calculate the window of the position, window size 10 000
        pos = pos19[1]
        residue = pos % 10000
        window = str(pos - residue)
        # get right format for location (chro:position)
        hg19_loc = results_chr + ":" + results_old
        hg38_loc = results_chr + ":" + results_new
        # retrieve the rs_id linked to the position from snp table
        cursor.execute("""
                SELECT rs_id FROM snp
                WHERE chromosome = ? AND position = ?;""",
                (results_chr, results_new))
        rs_id = cursor.fetchone()
        # insert all the info to the indexes table
        cursor.execute("""
                INSERT INTO indexes (rs_id, chromosome, GRCh37_position, GRCh37_loc, GRCh38_position, GRCh38_loc, GRCh37_window)
                VALUES (?,?,?,?,?,?,?)
                """, (rs_id[0],results_chr,results_old,hg19_loc,results_new,hg38_loc,window))
        conn.commit()
    except:
        continue

conn.close()
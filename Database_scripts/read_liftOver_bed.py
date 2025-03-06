import sqlite3
from pyliftover import LiftOver

# Connecting to sqlite
conn = sqlite3.connect('../Database/t2d_snp_portal.db')
 
# cursor object
cursor = conn.cursor()

# selecting rs_ids and hg38 info from snp for the indexes table
cursor.execute("SELECT DISTINCT rs_id,chromosome, position FROM snp")
hg38_pos = cursor.fetchall()


# create the indexes table
index_table = """CREATE TABLE indexes (
            rs_id VARCHAR(30) NOT NULL,
            chromosome INT,
            GRCh37_position INT,
            GRCh38_position INT
            ); """

cursor.execute(index_table)
conn.commit()

# populate the table with rs_ids and hg38 position info (from snp table)
for loc_info in hg38_pos:
    # parsing the info from each line
    rs = loc_info[0]
    chro = loc_info[1]
    pos = loc_info[2]
    cursor.execute("""
            INSERT INTO indexes (rs_id, chromosome, GRCh38_position)
            VALUES (?,?,?)
            """, (rs,chro,pos))
    conn.commit()

lo = LiftOver('hg17', 'hg18')
lo.convert_coordinate('chr1', 1000000)


# using the new generated bed file from LiftOver
# insert the correct bed file name here
with open("hglft_genome_2c5c93_76aec0.bed")as f:
    for line in f:
        # reading the bed file line by line
        parts = line.strip().split("\t")
        chromosome = parts[0].split("chr")[1]
        hg19 = parts[3].split("-")[1]
        hg38 = parts[1]
        # inserting the values to the indexes table based on the genomic position
        cursor.execute("""
            UPDATE indexes
            SET GRCh37_position = ?
            WHERE chromosome = ? AND GRCh38_position = ?""", 
            (hg19, chromosome, hg38))
        conn.commit()

conn.close()
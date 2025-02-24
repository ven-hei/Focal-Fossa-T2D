import sqlite3

conn = sqlite3.connect("t2d.db")
cursor = conn.cursor()

cursor.execute("SELECT rs_id, chromosome, position, location FROM snp;")
snps = cursor.fetchall()

output_file = "t2d_snp_database.txt"
with open(output_file, "w") as f:
    for snp in snps:
        rs_id, chromosome, position, location = snp
        f.write(f"{rs_id}\t{chromosome}\t{position}\t{location}\n")

conn.close()

print(f"SNP data (with location) has been exported to {output_file}")


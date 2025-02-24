import sqlite3

conn = sqlite3.connect("t2d.db")
cursor = conn.cursor()

# Query only the desired columns (excluding location)
cursor.execute("SELECT rs_id, chromosome, position FROM snp;")
snps = cursor.fetchall()

output_file = "t2d_snp_database.txt"
with open(output_file, "w") as f:
    # Write headers
    f.write("rs_id\tchromosome\tposition\n")
    for snp in snps:
        rs_id, chromosome, position = snp
        f.write(f"{rs_id}\t{chromosome}\t{position}\n")

conn.close()#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO 

print(f"SNP data (without location) has been exported to {output_file}")

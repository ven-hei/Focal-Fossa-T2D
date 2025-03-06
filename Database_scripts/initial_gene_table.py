import gget
import pandas as pd

import requests
import json
import os
import sqlite3

# Connecting to sqlite
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, '../Database/t2d_snp_portal.db')
conn = sqlite3.connect(database_path)

 
# cursor object
cursor = conn.cursor()

# drop the old table if exists
cursor.execute("DROP TABLE gene")
# create a new gene table with the requred column names
cursor.execute(""" CREATE TABLE gene (
            gene_index INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(100),
            full_name VARCHAR(255),
            description TEXT,
            chromosome INT, 
            start_pos INT, 
            end_pos INT,
            ensembl_acc_code VARCHAR(50),
            NCBI_gene_ID INT,
            uniprot_ID VARCHAR(30)
        ); """)
conn.commit()
# selecting unique ensembl accession codes for the primary key for the gene table
cursor.execute("""SELECT DISTINCT ensembl_acc_code from snp""")

gene_id = cursor.fetchall()

# going through all the ensembl accession codes one by one
for id in gene_id:
    # if records not found the try-except will handle it
    try:
        # calling gget to get info about the ensembl accession code and parse the needed information from the table
        one_id = gget.info([id[0]])
        symbol = str(one_id.iloc[0,6])
        ncbi_id = str(one_id.iloc[0,3])
        uniprot_id = str(one_id.iloc[0,1])
        uniprot_desc = str(one_id.iloc[0,12])
        full_name = str(one_id.iloc[0,11]) 
        chro = one_id.iloc[0,18]
        start = one_id.iloc[0,20]
        end = one_id.iloc[0,21]
        print(chro)
        print(start)
        print(end)
    
        # insert info to the gene table
        cursor.execute("""INSERT INTO gene (symbol, full_name, description, chromosome, start_pos, end_pos, ensembl_acc_code, NCBI_gene_ID, uniprot_ID) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                        (symbol, full_name, uniprot_desc, chro, start, end, id[0], ncbi_id, uniprot_id))
        conn.commit()
    except:
        continue

conn.close()
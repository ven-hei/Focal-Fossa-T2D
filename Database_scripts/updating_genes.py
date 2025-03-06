import gget
import pandas as pd

import requests
import json
import os
import sqlite3

# Connecting to sqlite
conn = sqlite3.connect('../Database/t2d_snp_portal.db')
 
# cursor object
cursor = conn.cursor()

# selecting unique ensembl accession codes that are only found from snp table to update gene table
not_in_table = cursor.execute("""SELECT DISTINCT ensembl_acc_code FROM snp
                    EXCEPT
                    SELECT ensembl_acc_code FROM gene""")
last_genes = cursor.fetchall()

# going through all the ensembl accession codes one by one
for code in last_genes:
    # if records not found the try-except will handle it
    try:
        # calling gget to get info about the ensembl accession code and parse the needed information from the table
        one_id = gget.info([code[0]])
        symbol = str(one_id.iloc[0,6])
        ncbi_id = str(one_id.iloc[0,3])
        uniprot_id = str(one_id.iloc[0,1])
        uniprot_desc = str(one_id.iloc[0,12])
        full_name = str(one_id.iloc[0,11]) 
    
        # insert info to the gene table
        cursor.execute("""INSERT INTO gene (symbol, full_name, description, ensembl_acc_code, NCBI_gene_ID, uniprot_ID) 
                        VALUES (?, ?, ?, ?, ?, ?)""", 
                        (symbol, full_name, uniprot_desc, code[0], ncbi_id, uniprot_id))
        conn.commit()
    except:
        continue

conn.close()
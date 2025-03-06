import gget
import pandas as pd

import requests
import json
import os
import sqlite3


file="data.json"

# remove the old json file if it exists
if os.path.isfile(file):
    os.remove(file)

# the url to the gwas data
# type 2 diabetes MONDO id: MONDO_005148 used to filter the correct accessions
url = "https://www.ebi.ac.uk/gwas/rest/api/efoTraits/MONDO_0005148/associations"

# to make it look like a normal internet search
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, kuten Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# requesting the infomation from the url
response = requests.get(url, headers=headers)

if response.status_code == 200:
    # save the response as json
    x = response.json()
    with open(file, "w") as f:
        # write into the file
        f.write(json.dumps(x, indent=4))
else:
    print(f"Error: {response.status_code}")

# open the json file
json_data = open("data.json") # change to data when using the actual data

data = json.load(json_data)

# Connecting to sqlite
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, '../Database/t2d_snp_portal.db')
conn = sqlite3.connect(database_path)
 
# cursor object
cursor = conn.cursor()


cursor.execute("""CREATE TABLE updates (
            rs_id VARCHAR(50) NOT NULL,
            last_update VARCHAR(50)
        ); """)
conn.commit()

associations = data["_embedded"]["associations"]

sep = "-"
# parse the json file based on different values
for association in associations:
    for locus in association.get("loci",[]):
        for snp in locus.get("strongestRiskAlleles",[]):
            # risk allele is part of the rs id and it is removed in this step
            risk_al = snp.get("riskAlleleName")
            rs = risk_al.split(sep, 1)[0]
            # if rs id is not in correct format (e.g. instead of rs id it is chromosome position) it is not included in the database
            if "rs" in rs:
                rs_id = rs # cleaned rs id is saved to variable
            else:
                rs_id = "not"
    update = association.get("lastUpdateDate")

    cursor.execute("""
                    INSERT INTO updates (rs_id, last_update) 
                    VALUES (?, ?)""", 
                    (rs_id, update))
    conn.commit()
        # cursor.execute("""
        #             INSERT INTO gene (symbol, ensembl_acc_code, NCBI_gene_ID) 
        #             VALUES (?, ?, ?)""", 
        #             (mapped_gene, ensembl_id, ncbi_id))


# compare_updates = cursor.execute("""SELECT rs_id FROM snp
#                     EXCEPT
#                     SELECT ensembl_acc_code FROM gene""")
# last_genes = cursor.fetchall()
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

# loading the data from the json file to the variable for parsing
data = json.load(json_data)

app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, '../Database/t2d_snp_portal.db')
conn = sqlite3.connect(database_path)
 
# cursor object
cursor = conn.cursor()

# select associations directory from json file
associations = data["_embedded"]["associations"]

sep = "-"
# parse the json file based on different values
for association in associations:
    # collecting the p value
    p_value = association.get("pvalue")
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

        # collecting the ensembl accession code
        for gene in locus.get("authorReportedGenes",[]):
            for ensembl in gene.get("ensemblGeneIds"):
                ensembl_id = ensembl.get("ensemblGeneId")
    
    # if the rs id was in correct format the location of that rs id is queried and the chromosome and the position is recorded from another GWAS record
    if rs_id != "not":
        file_loci = "loci.json"
        # accessing the location info based on the rs id
        loci_url = "https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/" + rs_id
        response_rs = requests.get(loci_url, headers=headers)
        
        # if clause to handle the possible errors from the GWAS record
        if response_rs.status_code == 200:
        # save the response as json
            x = response_rs.json()
            with open(file_loci, "w") as f_l:
                # write into the file
                f_l.write(json.dumps(x, indent=4))
        else:
            print(f"Error: {response_rs.status_code}")

        # open the json file
        json_loci_data = open("loci.json") # change to data when using the actual data

        # loading the variable with the data
        data_loci = json.load(json_loci_data)

        # parsing the json file to access the chromosome and the base position
        location = data_loci["locations"]
        for locus in location:
            chro = locus.get("chromosomeName")
            pos = locus.get("chromosomePosition")
        
        # combining the values together for the search page
        loc = str(chro) + ":" + str(pos)

        # insert all the acquired data to the sql database
        cursor.execute("""
                    INSERT INTO snp (rs_id, chromosome, position, location, p_value, ensembl_acc_code) 
                    VALUES (?, ?, ?, ?, ?, ?)""", 
                    (rs_id, chro, pos, loc, p_value, ensembl_id))
        conn.commit()
        
        json_loci_data.close()
        os.remove(file_loci)


# select ensembl ids and create gene table

conn.close()


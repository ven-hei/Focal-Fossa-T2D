
import requests
import json
import os
import sqlite3

conn = sqlite3.connect('../Database/t2d_snp_portal.db')
 
# cursor object
cursor = conn.cursor()

# parsing the location of each rs_id
rs_list_sql = cursor.execute("""SELECT rs_id FROM snp""")
rs_list = cursor.fetchall()
#print(rs_list)

# to make it look like a normal internet search
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, kuten Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
file_loci = "loci.json"

for rs in rs_list:
    loci_url = "https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/" + rs[0]
    response_rs = requests.get(loci_url, headers=headers)
    if response_rs.status_code == 200:
    # save the response as json
        x = response_rs.json()
        with open(file_loci, "w") as f:
            # write into the file
            f.write(json.dumps(x, indent=4))
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

    # adding the values to the sql table
    cursor.execute("""
                   UPDATE snp 
                   SET chromosome = ?, position = ?, location =? 
                   WHERE rs_id = ?""", 
                   (chro, pos, loc, rs[0]))
    conn.commit()

    #print(chro)
    #print(pos)
    #print(loc)
    json_loci_data.close()
    os.remove(file_loci)


conn.close()
import gget
import pandas as pd
import sqlite3
import datetime
import os
import requests
import json
from pyliftover import LiftOver

# Connecting to sqlite
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, '../Database/t2d_snp_portal.db')
conn = sqlite3.connect(database_path)
 
# cursor object
cursor = conn.cursor()
 
# accessing the last date in the accessed table to check last update date
last_update_sql = """SELECT MAX(date) FROM accessed;""" # technically this line works since the dates will get bigger each time
cursor.execute(last_update_sql)
last_update = cursor.fetchone()
last_update = last_update[0]

# checking user's date
today = datetime.datetime.now().strftime("%Y-%m-%d")

# update based on the updates in the original source (GWAS)
if last_update != today:
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

    # if the connection to GWAS works
    if response.status_code == 200:
        # save the response as json
        x = response.json()
        with open(file, "w") as f:
            # write into the file
            f.write(json.dumps(x, indent=4))

        json_data = open("data.json") # change to data when using the actual data

        data = json.load(json_data)
        #creating a temporary table in the t2d database to check whether there has been changes
        cursor.execute("""CREATE TABLE updates (
                    rs_id VARCHAR(50) NOT NULL,
                    last_update VARCHAR(50)
                ); """)
        conn.commit()

        # collect the update dates from json and add them to the temporary table
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
            # collecting the last update dates for the temporary updates table
            update = association.get("lastUpdateDate")

            # not including rs ids that are not in correct format
            # the datapoints with correct rs ids will be inserted to the database
            if rs_id != "not":
                cursor.execute("""
                                INSERT INTO updates (rs_id, last_update) 
                                VALUES (?, ?)""", 
                                (rs_id, update))
                conn.commit()

        # compare snp table in t2d and the temporary updates table to see if there are any changes
        compare_tables = cursor.execute("""SELECT rs_id, last_update FROM snp
                            EXCEPT
                            SELECT * FROM updates
                            UNION ALL
                            SELECT * FROM updates
                            EXCEPT
                            SELECT rs_id, last_update FROM snp           
                            """)
        num_updates = cursor.fetchall()

        # checking the length of the results from the union. If length is more than 0 it means there has been changes
        update_check = len(num_updates)

        # deleting the temporary updates table once it has been compared to the old database
        conn.execute("DROP TABLE updates")
        
        # the new today date is added to the access table
        cursor.execute("INSERT INTO accessed (date) VALUES (?)", (today,))
        conn.commit()

         # If the database is not updated the the old snp table will be removed and new one will be generated. 
        # The gene table will be checked based on the updated snp table
        if update_check != 0:
            conn.execute("DROP TABLE snp")

            # Creating new tables 
            snp_table = """ CREATE TABLE snp (
                        snp_index INTEGER PRIMARY KEY AUTOINCREMENT,
                        rs_id VARCHAR(30) NOT NULL,
                        chromosome INT,
                        position INT,
                        location VARCHAR(50),
                        p_value FLOAT,
                        ensembl_acc_code VARCHAR(50),
                        last_update VARCHAR(70),
                        FOREIGN KEY (ensembl_acc_code) REFERENCES gene(ensembl_acc_code)
                    ); """
            
            cursor.execute(snp_table)
            conn.commit()

            # going through the json file and parsing the needed info from it
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
                
                # collecting the last updated date from the gwas
                update = association.get("lastUpdateDate")
            
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
                        # give error if the connection to GWAS unsuccessful
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
                                INSERT INTO snp (rs_id, chromosome, position, location, p_value, ensembl_acc_code, last_update) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                                (rs_id, chro, pos, loc, p_value, ensembl_id, update))
                    conn.commit()

                    # closing the json file and remove the json file containing location info 
                    json_loci_data.close()
                    os.remove(file_loci)
        
        # removing the json file containing the data
        json_data.close()
        os.remove(file)


        # checking if there are differences between teh genes in snp table and gene table in order to update the gene table
        not_in_table = cursor.execute("""SELECT DISTINCT ensembl_acc_code FROM snp
                            EXCEPT
                            SELECT ensembl_acc_code FROM gene""")
        last_genes = cursor.fetchall()

        # only updating the genes the new genes to the database
        if len(last_genes) != 0:
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
                    continue # ingnore errors/warnings/missing data
            
        # comparing the snp table and indexes tables in order to update indexes table
        not_in_indexes = cursor.execute("""SELECT DISTINCT rs_id FROM snp
                            EXCEPT
                            SELECT DISTINCT rs_id FROM indexes""")
        new_snps = cursor.fetchall()

        if len(new_snps) != 0:
            # select location info from fst table, the position info for hg19
            cursor.execute("SELECT chromosome, start_position FROM fst")
            hg19_pos = cursor.fetchall()

            # remove the old indexes table
            cursor.execute("DROP TABLE IF EXISTS indexes")
            conn.commit()
            #print("here")
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
    
    # print an error if the connection to GWAS does not work
    else:
        print(f"Error: {response.status_code}")


# closing the connection to the database
conn.close()
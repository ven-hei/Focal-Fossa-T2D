import sqlite3

### First time creating the tables in the database

# connection to the database
conn = sqlite3.connect('./Database/t2d_snp_portal.db')
cursor = conn.cursor()

# defining the content of each table
# initial snp data, for the search results
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
    
# gene info table, for the gene page
gene_table = """ CREATE TABLE gene (
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
        ); """

# accessed table used for the database updates
date_table = """CREATE TABLE accessed (
            date_index INTEGER PRIMARY KEY AUTOINCREMENT,
            date VARCHAR(50) NOT NULL
        ); """


# adding the tables to the database
cursor.execute(snp_table)
cursor.execute(gene_table)
cursor.execute(date_table)

conn.commit()

conn.close()
import sqlite3

### First time creating the tables in the database

# connection to the database
conn = sqlite3.connect('../Database/t2d.db')
cursor = conn.cursor()

# defining the content of each table
# initial snp data, for the search results
snp_table = """ CREATE TABLE snp (
            rs_id VARCHAR(30) NOT NULL,
            chromosome INT,
            position INT,
            location VARCHAR(50),
            p_value FLOAT,
            ensembl_acc_code VARCHAR(100),
            last_update VARCHAR(70)
        ); """
    
# gene info table, for the gene page
gene_table = """ CREATE TABLE gene (
            symbol VARCHAR(100) NOT NULL,
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
            date VARCHAR(50) NOT NULL
        ); """

# tajima d result table for population stats
tajima_d_table = """CREATE TABLE tajima_d (
            chromosome INT,
            start_position INT,
            tajima_d_BEB FLOAT,
            tajima_d_ITU FLOAT,
            tajima_d_GIH FLOAT,
            tajiima_d_PJL FLOAT
        ); """

# fst results for population stats
fst_table = """CREATE TABLE fst (
            chromosome INT,
            start_position INT,
            fst_EUR_BEB FLOAT,
            fst_EUR_ITU FLOAT,
            fst_EUR_GIH FLOAT,
            fst_EUR_PJL FLOAT
        ); """


# adding the tables to the database
cursor.execute(snp_table)
cursor.execute(gene_table)
cursor.execute(date_table)
cursor.execute(tajima_d_table)
cursor.execute(fst_table)

conn.commit()

conn.close()
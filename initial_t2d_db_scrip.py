import sqlite3

### First time creating the tables in the database

# connection to the database
conn = sqlite3.connect('Database/focal_fossa.db')
cursor = conn.cursor()

# defining the content of each table
snp_table = """ CREATE TABLE snp (
            rs_id VARCHAR(30) NOT NULL,
            chromosome INT,
            position INT,
            location VARCHAR(50),
            p_value FLOAT,
            ensembl_acc_code VARCHAR(100),
            last_update VARCHAR(70)
        ); """
    
gene_table = """ CREATE TABLE gene (
            symbol VARCHAR(100) NOT NULL,
            full_name VARCHAR(255),
            description TEXT,
            ensembl_acc_code VARCHAR(50),
            NCBI_gene_ID INT,
            uniprot_ID VARCHAR(30)
        ); """

date_table = """CREATE TABLE accessed (
            date VARCHAR(50) NOT NULL
        ); """


# adding the tables to the database
cursor.execute(snp_table)
cursor.execute(gene_table)
cursor.execute(date_table)


conn.commit()


conn.close()
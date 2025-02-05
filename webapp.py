from flask import Flask, render_template, url_for, redirect, request
import sqlite3
import pandas as pd

app = Flask(__name__)

# Connect to available database
def get_db_connection():
    conn = sqlite3.connect('Database/web_database.db')
    conn.row_factory = sqlite3.Row  
    return conn

# create a route for the home page
@app.route("/")
def home():
    return render_template('home.html')

# create new route for search results to show result on new page
@app.route("/search-result")
def result():
    query = request.args.get('query', '').strip()  # search for key words
    results = []
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        # retrieve information from the db for the SNP table
        cursor.execute("""
            SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
            WHERE STRONGEST_SNP_RISK_ALLELE LIKE ? OR REGION LIKE ? OR MAPPED_GENE LIKE ?
            ORDER BY STRONGEST_SNP_RISK_ALLELE
        """, (query, query, query)) # with out '%'s the search is more accurate
        results = cursor.fetchall()
        # retrieve infromation from the db to find all the possible populations
        cursor.execute("""
            SELECT DISTINCT population FROM association 
            WHERE STRONGEST_SNP_RISK_ALLELE LIKE ? OR REGION LIKE ? OR MAPPED_GENE LIKE ?
            """, (query, query, query))
        populations = cursor.fetchall()
        conn.close()

    return render_template('search-result.html', results=results, query=query, populations=populations)
    
# create route for gene function page
@app.route('/gene/<gene_name>')
def gene(gene_name):
    geneconnect = get_db_connection()
    gene_table = pd.read_sql_query("SELECT * FROM gene_info", geneconnect)
    gene_table['symbol'] = gene_table['symbol'].astype(str)

    # ensuring capital letters in gene names
    gene_name = gene_name.upper().strip()

    # trying to extract row for the specified gene
    try:
        row = gene_table.loc[gene_table['symbol'] == gene_name].iloc[0]
        # if specified gene found from the dataframe, return information about it
        return render_template('gene_detail.html', name = gene_name, \
                                full_name = row.full_name,\
                                term = row.functional,\
                                database = row.database,\
                                acc_code = row.accession_code, \
                                link = row.db_link, \
                                loc = row.location, \
                                desc = row.description)
    except:
        # if gene not found -> key error
        return f"We don't have any information about this gene called {gene_name}"

# create route to population statistics page
@app.route('/population_stats/<population_name>')
def population(population_name):
    return render_template('population_stats.html', name=population_name)


@app.route("/about")
def about():
    return render_template('about.html')
app.run(host="0.0.0.0", port=81) 
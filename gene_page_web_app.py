import pandas as pd
from flask import Flask, render_template,url_for,redirect
import sqlite3
import csv

# importing libraries
from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField
from wtforms.validators import InputRequired

# create flask application object
app = Flask(__name__)

# secret key for later
app.config['SECRET_KEY'] = 'change this unsecure key'

# tell code where to find the data
geneconnect = sqlite3.connect('gene.db')

#query = geneconnect.execute("SELECT * From gene_info")
#cols = [column[0] for column in query.description]
#gene_table= pd.DataFrame.from_records(data = query.fetchall(), columns = cols)
#gene_table['symbol'] = gene_table['symbol'].astype(str)

#print(gene_table)

# reading the data from the database file to pandas dataframe
gene_table = pd.read_sql_query("SELECT * FROM gene_info", geneconnect)
gene_table['symbol'] = gene_table['symbol'].astype(str)

# define the action for the top level route
@app.route('/')
def index():
    return 'Welcome to TD2 SNP Portal'

@app.route('/gene/<gene_name>')
def gene(gene_name):

    # ensuring capital letters in gene names
    gene_name = gene_name.upper().strip()

    # trying to extract row for the specified gene
    try:
        row = gene_table.loc[gene_table['symbol'] == gene_name].iloc[0]
        # if specified gene found from the dataframe, return information about it
        return render_template('gene_page.html', name = gene_name, \
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
    
# start the web server
if __name__ == '__main__':
    app.run(debug = True)
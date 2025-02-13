from flask import Flask, render_template, url_for, redirect, request
import sqlite3
import pandas as pd
import os
from flask_wtf import FlaskForm
from wtforms import SearchField, StringField, SubmitField,SelectField,SelectMultipleField,IntegerField,RadioField,widgets
from wtforms.validators import DataRequired


app = Flask(__name__)
app.config['SECRET_KEY'] = 'f41676960aa9bdaa1122637d89ef298f'


# using path of web application as path of database to avoid error when deploy web app
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "Database/web_database.db")

# Connect to available database
def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn

# create a route for the home page
@app.route("/")
def home():
    return render_template('home.html')

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class SummaryStatsForm(FlaskForm):
    population = MultiCheckboxField('What population(s) do you want to analyze?')
    stats_parameter = MultiCheckboxField('Choose parameter(s) for further analysis:',
                                          choices=[('pi','Pi'),('fst','Fst'),('dxy','Dxy'),('taji',"Tajima's D"),('all','All')],
                                          )
    region = IntegerField('What is the region of your interest?',validators=[DataRequired()])
    submit = SubmitField('Continue >>')

# create new route for search results to show result on new page
@app.route("/search-result")
def result():
    query = request.args.get('query','', type=str).strip()
    search_option = request.args.get('search_option', type=str)
    page = request.args.get('page',1, type=int)
    number_of_result_displayed = request.args.get('number_of_result_displayed',20, type=int)

    results = []
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        if not search_option:
            cursor.execute("""
                SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
                WHERE STRONGEST_SNP_RISK_ALLELE LIKE ? OR REGION LIKE ? OR MAPPED_GENE LIKE ?
                ORDER BY STRONGEST_SNP_RISK_ALLELE
            """, (query,query,query))
        elif search_option == 'SNP_search':
            cursor.execute("""
                SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
                WHERE STRONGEST_SNP_RISK_ALLELE LIKE ?
                ORDER BY STRONGEST_SNP_RISK_ALLELE
            """, (query,))

        # change to location search ex 10:100231 in database, not seperate columns
        elif search_option == 'location_search':
            # (chromosome_ID,chromosome_position) = tuple(query.split(':'))
            # cursor.execute("""
            #     SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
            #     WHERE CHR_ID = ? OR CHR_POS LIKE ?
            #     ORDER BY STRONGEST_SNP_RISK_ALLELE
            # """, (chromosome_ID, chromosome_position + '%' )) 
            cursor.execute("""
                SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
                WHERE coordinate_location LIKE ?
                ORDER BY STRONGEST_SNP_RISK_ALLELE
            """, (query,)) 
        else:
            cursor.execute("""
                SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
                WHERE MAPPED_GENE LIKE ?
                ORDER BY STRONGEST_SNP_RISK_ALLELE
            """, (query,))
        
        results = cursor.fetchall()
        # retrieve infromation from the db to find all the possible populations
        cursor.execute("""
            SELECT DISTINCT population FROM association 
            WHERE STRONGEST_SNP_RISK_ALLELE LIKE ? OR REGION LIKE ? OR MAPPED_GENE LIKE ?
            """, (query, query, query))
        populations = cursor.fetchall()
        conn.close() 

    #create dynamic choices from above population       
    population_values = [dict(row).get('population') for row in populations]
    population_values = [x for x in population_values if (x!='' and x is not None)]
    population_choices=[]
    for population in population_values:
        population_choices.append((population,population))
    if len(population_choices)>1:
        population_choices.append(('all','All'))

    form = SummaryStatsForm()
    form.population.choices = population_choices 
    
    # add number of results will be displays and split results into multiple page
    number_of_results = len(results)
    number_of_pages = (number_of_results//number_of_result_displayed) + 1

    results_displayed=[]
    if results:
         results_displayed = results[((page-1)*number_of_result_displayed) : (page*number_of_result_displayed)]


    return render_template('search-result.html', 
                           results_displayed=results_displayed, 
                           query=query, 
                           search_option=search_option, 
                           number_of_pages=number_of_pages,
                           number_of_results=number_of_results,
                           page=page,
                           number_of_result_displayed=number_of_result_displayed,
                           populations = populations,
                           form=form) #CHECK exception
    

# create route for gene function page
@app.route('/gene/<gene_name>')
def gene(gene_name):
    geneconnect = sqlite3.connect(database_path)
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

# create route to population about page
@app.route("/about")
def about():
    return render_template('about.html')

@app.route('/summary-stats-result')
def summary_stats_result():
    population_for_stats=request.args.getlist('population')
    parameter_for_stats=request.args.getlist('stats_parameter')
    region_for_stats=request.args.get('region')
    return render_template('summary-stats-result.html',
                           population_for_stats=population_for_stats,
                           parameter_for_stats=parameter_for_stats,
                           region_for_stats=region_for_stats)

app.run(host="0.0.0.0", port=81) 

# when deploy webapp, using that:
# if __name__ == '__main__':
#     app.run(debug=True)
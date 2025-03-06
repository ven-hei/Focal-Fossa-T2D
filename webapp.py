from flask import Flask, flash, render_template, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms import SelectField,SelectMultipleField,widgets,BooleanField,StringField
from wtforms.validators import DataRequired
import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt
import subprocess

# initialize the app and set the secret key
app = Flask(__name__)
app.config['SECRET_KEY'] = 'this_is_a_secret_key'

# using path of web application to direct to database to avoid error when deploy web app
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "Database/t2d_snp_portal.db")


# Connect to available database
def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row # to access the columns by name
    return conn

# Retrieving last updated date from the database, accessed table, for the home page
def last_update_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    last_update_sql = """SELECT MAX(date) FROM accessed;""" # technically this line works since the dates will get bigger each time
    cursor.execute(last_update_sql)
    last_updated = cursor.fetchone()
    last_updated = last_updated[0]
    return last_updated

# define population abbreviation and population name dictionary
population_abbr = {'BEB': 'Bengali', 
                   'GIH': 'Gujarati', 
                   'ITU': 'Indian', 
                   'PJL': 'Punjabi', 
                   'EUR': 'European'}

# define population choices for summary statistics form
populations_for_choices = [(pop,population_abbr.get(pop)) for pop in population_abbr.keys() if pop != 'EUR']
populations_for_choices.append(("all","All"))

# define choices for chromosome
chromosome_choices = [str(i) for i in range(1,23)]
chromosome_choices.append('X')

# create a custom multi checkbox field
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


# create form class for summary statistics
class SummaryStatsForm(FlaskForm):
    population = MultiCheckboxField('What population(s) do you want to analyse?',
                                    choices= populations_for_choices)
    stats_parameter = MultiCheckboxField('Choose parameter(s) for summary statistics:',
                                          choices=[('fst','Fst'),
                                                   ('tajimas_d',"Tajima's D"),
                                                   ('all','All')],
                                          )
    region_input = BooleanField('Click here if you want to change genomic region of interest',default=False)
    chromosome_no = SelectField('Chromosome:',choices=chromosome_choices,validators=[DataRequired()])
    start_position = StringField('Start position:',validators=[DataRequired()])
    end_position = StringField('End position',validators=[DataRequired()])

# create a route for the home page
@app.route("/")
def home():
    last_update = last_update_db()
    return render_template('home.html', last_updated = last_update)

# create a route for updating the database
@app.route("/update_db", methods = ["POST"])
def update_db():
    try:
        # running the database script to update the database
        subprocess.run(["python", "Database_scripts/database_script.py"], check = True)
    except Exception as e: # if update is unsuccessful error will be returned to the user
        return render_template("home.html", message = "Error updating database", last_updated = last_update_db())
    return redirect(url_for("home"))

# create new route for search results to show result on new page
@app.route("/search-result")
def result():
    query = request.args.get('query','', type=str).strip()
    search_option = request.args.get('search_option', type=str)
    page = request.args.get('page',1, type=int)
    number_of_result_displayed = request.args.get('number_of_result_displayed',20, type=int) # number of results displayed per page

    results = []
    
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()

        # If user selects SNP_search and inputs rs ID for search
        if search_option == 'SNP_search':
            # Joining the snp and gene tables together in order to retrieve all needed information for the search result page
            cursor.execute("""
                SELECT a.rs_id, a.location, a.p_value, b.symbol FROM snp a
                INNER JOIN gene b ON a.ensembl_acc_code = b.ensembl_acc_code
                WHERE a.rs_id LIKE ?
                ORDER BY a.rs_id
            """, (query,))

            form=None # no form will be passed to the search result page

            results = cursor.fetchall()

        # If user selects location_search and inputs genomic region
        elif search_option == "location_search":   
            try:
                query=query.upper()
                (chromosome,position)=query.split(':')
                (start_position,end_position)=position.split('-')
                if int(start_position)>int(end_position):
                    # add flash message later
                    flash('You have entered invalid genomic coordinate. Please try again!\
                          Right genomic coordinate format: chromosome:start_position-end_position')
                    #redirect to home page for user to try again
                    return redirect(url_for('home'))

                # Joining the snp and gene tables together in order to retrieve all needed information for the search result page
                cursor.execute("""
                        SELECT a.rs_id, a.location, a.p_value, b.symbol FROM snp a
                        INNER JOIN gene b ON a.ensembl_acc_code = b.ensembl_acc_code
                        WHERE a.chromosome = ? and a.position >= ? and a.position <= ?
                        ORDER BY a.position
                    """, (chromosome,start_position,end_position))


                # Pass the region user searched for to the form
                form=SummaryStatsForm()
                form.chromosome_no.data=chromosome
                form.start_position.data=start_position
                form.end_position.data=end_position
                
                results = cursor.fetchall()

            except:
                # add flash message
                flash('You have entered invalid genomic coordinate. Please try again!\
                      Right genomic coordinate format: chromosome:start_position-end_position')
                #redirect to home page for user to try again
                return redirect(url_for('home')) 
        
        # If user selects gene search and inputs the short gene name
        else:
            # Joining the snp and gene tables together in order to retrieve all needed information for the search result page
            cursor.execute("""
                SELECT a.rs_id, a.location, a.p_value, b.symbol FROM snp a
                INNER JOIN gene b ON a.ensembl_acc_code = b.ensembl_acc_code
                WHERE b.symbol LIKE ?
                ORDER BY a.rs_id
                """, (query,))
            

            results = cursor.fetchall()

            # get genomic location of the searched gene to pass to the form
            cursor.execute("""
                SELECT chromosome, start_pos, end_pos FROM gene 
                WHERE symbol LIKE ?
            """, (query,))
            
            gene_locations = cursor.fetchall()

            # if gene found in the database
            if len(gene_locations) == 1:
                (chromosome,start_position,end_position) = gene_locations[0]

                # Pass the genomic location of the gene to the form
                form=SummaryStatsForm()
                form.chromosome_no.data=chromosome
                form.start_position.data=start_position
                form.end_position.data=end_position
            
            # if no gene found in the database user have to input the region manually
            # in case user want to calculate summary statistics
            else: 
                form = SummaryStatsForm()
                form.region_input.data=True
    
    conn.close()
    
    # add number of results will be displayed and split results into multiple page
    number_of_results = len(results)
    total_pages = (number_of_results//number_of_result_displayed) + 1
    results_displayed=[]
    if results:
        results_displayed = results[((page-1)*number_of_result_displayed) : (page*number_of_result_displayed)]

    return render_template('search-result.html', 
                           results_displayed=results_displayed, 
                           query=query, 
                           search_option=search_option, 
                           total_pages=total_pages,
                           number_of_results=number_of_results,
                           page=page,
                           number_of_result_displayed=number_of_result_displayed,
                           form=form)
    

# create route for gene function page
@app.route('/gene/<gene_name>')
def gene(gene_name):
    # convert gene name to uppercase
    gene_name = gene_name.upper()
        
    # get gene information from database
    conn=get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM gene WHERE symbol = ?""",(gene_name,))
    gene_info = cursor.fetchone()
    conn.close()

    # if gene not found in the database, show flash message
    if gene_info is None:
        flash(f"We don't have any information about this gene called {gene_name}")
        return render_template('gene_detail.html',gene_info=None)
    
    # if gene found, show gene information and add link to NCBI
    else:
        gene_info = dict(gene_info)

        # split gene description into list of sentences
        gene_info['description'] = gene_info['description'].split(". ")
        
        # add link to NCBI website
        gene_info['ncbi_link'] = f"https://www.ncbi.nlm.nih.gov/gene/{gene_info['NCBI_gene_ID']}"
        
        return render_template('gene_detail.html', gene_info=gene_info)


# define function to plot Tajima's D
def plot_tajimas_d(data_tajima,chromosome,population):
    plt.figure(figsize=(12, 6))
    x=data_tajima.index # start position of each window is used as index later and plotted on x-axis
    y=data_tajima[f'tajima_d_{population}']

    # Plot scatter for each base pair value
    plt.scatter(x,y, color='blue', alpha=0.6,s=10, label="Tajima's D (Scatter)")
    plt.axhline(y=0, color='red', linestyle='--',label="Neutral expectation") # plot neutral expectation line
    plt.xlabel("Genomic position (bp)")
    plt.ylabel("Tajima's D values")
    plt.title(f"Tajima's D for {population_abbr.get(population)} (Chromosome {chromosome})")
    plt.legend(loc='upper right')
    try:
        plt.ylim(y.min()-0.8,y.max()+0.8) # set y-axis limit
    except:
        pass

    # Save plot as image
    plot_path = os.path.join(app_path,'static/plots',f'plot_tajimas_d_{population}.png')
    plt.savefig(plot_path,dpi=500,bbox_inches='tight')
    plt.close()


# define function to plot Fst
def plot_fst(data_fst,chromosome,pop1,pop2):
    plt.figure(figsize=(12, 6))
    x=data_fst.index # position of each SNP is used as index later and plotted on x-axis
    y=data_fst[f'fst_{pop1}_{pop2}']
    plt.scatter(x,y, color='blue', s=10, alpha=0.6,label=f"FST Values ({pop2})")
    plt.axhline(y=y.mean(), color='red', linestyle='--',label=f"Average Fst = {y.mean():.4f}") # plot average Fst line
    plt.xlabel("Genomic position (bp)") 
    plt.ylabel("Fst values")
    plt.title(f"Fst between {population_abbr.get(pop1)} and {population_abbr.get(pop2)} (Chromosome {chromosome})")
    plt.legend(loc='upper right')   
    
    # Save plot as image
    plot_path = os.path.join(app_path,'static/plots',f'plot_fst_{pop1}_{pop2}.png')
    plt.savefig(plot_path,dpi=500,bbox_inches='tight')
    plt.close()


@app.route('/summary-stats-result')
def summary_stats_result():
    # get user selection for populations from form
    population_for_stats=request.args.getlist('population')
    if 'all' in population_for_stats:
        population_for_stats = ['BEB','GIH','ITU','PJL']

    # get user selection for statistics metric from form
    stats_metric=request.args.getlist('stats_parameter')
    if 'all' in stats_metric:
        stats_metric = ['tajimas_d','fst']

    # get user input for genomic region from form
    chromosome_no = request.args.get('chromosome_no')
    

    # replace comma with empty string and convert to integer
    start_position = request.args.get('start_position')
    start_position = int(start_position.replace(',',''))
    

    # replace comma with empty string and convert to integer
    end_position = request.args.get('end_position')
    end_position = int(end_position.replace(',',''))
    
    
    if 'tajimas_d' in stats_metric:
        # read data from database
        conn = sqlite3.connect(database_path)
        tajima_d_column_list = [f'tajima_d_{pop}' for pop in population_for_stats]
        data_tajima=pd.read_sql_query(f"""SELECT start_position, {', '.join(tajima_d_column_list)} FROM tajima_d
        WHERE chromosome = "{chromosome_no}" and start_position > {start_position-10000} and start_position < {end_position}
        ORDER BY start_position""",conn,dtype={x:float for x in tajima_d_column_list})
        conn.close()

        # if no data of Tajima's D found for the region, show flash message and redirect to summary statistics page
        if data_tajima.empty:
            flash(f"No data found for region {chromosome_no}:{start_position}-{end_position}. Please try again!")
            return redirect(url_for('sumstats'))
        
        # set start position as index
        data_tajima.set_index('start_position',inplace=True)

        # Write Tajima's D data to text file and plot
        tajimas_d_file_path = os.path.join(app_path,'static/download/summary_statistics(tajimas_d).txt')
        tajimas_d_file = open(tajimas_d_file_path,'wt')
        tajimas_d_file.write(f"----- Tajima's D for region {chromosome_no}:{start_position}-{end_position}-----\n")
        tajimas_d_file.write('Population\tAverage\tStandard deviation\n')
        
        for pop in population_for_stats:

            # Plot Tajima's D for each population
            plot_tajimas_d(data_tajima,chromosome_no,pop)

            # Calculate average and standard deviation of Tajima's D for each population and write to text file
            mean = str(data_tajima[f"tajima_d_{pop}"].mean())
            std = str(data_tajima[f"tajima_d_{pop}"].std())
            tajimas_d_file.write(f'{pop} ({population_abbr.get(pop)})\t{mean}\t{std}\n')

        # Write Tajima's D data to text file   
        tajimas_d_file.write('\n')
        tajimas_d_file.write(data_tajima.to_string(index=True))
        tajimas_d_file.close()
        
    if 'fst' in stats_metric:
        # read data from database
        conn = sqlite3.connect(database_path)
        fst_column_list=[f'fst_EUR_{pop}' for pop in population_for_stats]
        data_fst=pd.read_sql_query(f"""SELECT start_position, {', '.join(fst_column_list)} FROM fst
        WHERE chromosome = "{chromosome_no}" and start_position >= {start_position} and start_position <= {end_position}
        ORDER BY start_position""",conn,dtype={x:float for x in fst_column_list})
        conn.close()
        
        # if no data of Fst found for the region, show flash message and redirect to summary statistics page
        if data_fst.empty:
            fst_result = None

        else:
            fst_result = True
            # set start position as index
            data_fst.set_index('start_position',inplace=True)

            # Write Fst data to text file and plot
            fst_file_path = os.path.join(app_path,'static/download/summary_statistics(fst).txt')
            fst_file = open(fst_file_path,'wt')
            fst_file.write(f"----- Fixtion index (Fst) for region {chromosome_no}:{start_position}-{end_position} -----\n")
            
            # Write population abbreviation to text file
            for pop in population_for_stats:
                fst_file.write(f"{pop}: {population_abbr.get(pop)}\n")

            fst_file.write('Population\tAverage\tStandard deviation\n')
            pop1 = 'EUR'
            for pop2 in population_for_stats:
                # Plot Fst between each pair of populations
                plot_fst(data_fst,chromosome_no,pop1,pop2)

                # Calculate average and standard deviation of Fst between each pair of populations and write to text file
                mean = str(data_fst[f"fst_{pop1}_{pop2}"].mean())
                std = str(data_fst[f"fst_{pop1}_{pop2}"].std())
                fst_file.write(f'Fst_{pop1}_{pop2}\t{mean}\t{std}\n')

            # Write Fst data to text file
            fst_file.write('\n')
            fst_file.write(data_fst.to_string(index=True))
            fst_file.close()

    return render_template('summary-stats-result.html',
                           population_for_stats=population_for_stats,
                           stats_metric=stats_metric,
                           chromosome_no=chromosome_no,
                           start_position=start_position,
                           end_position=end_position,
                           population_abbr=population_abbr,
                           fst_result=fst_result)


# create route to summary statistics page
@app.route('/summary_statistics')
def sumstats():

    # Create a form for summary statistics
    form = SummaryStatsForm()
    
    return render_template("summary_statistics.html", form=form)


# create route to documentation page
@app.route("/documentation")
def documentation():
    return render_template('documentation.html')


# create route to about page
@app.route("/about")
def about():
    return render_template('about.html')

# to run the webapp locally
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

# # when deploy webapp, using that:
# if __name__ == '__main__':
#     app.run(debug=True)

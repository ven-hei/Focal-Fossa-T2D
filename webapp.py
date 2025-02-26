from flask import Flask, flash, render_template, url_for, redirect, request
from flask_wtf import FlaskForm
from wtforms import SearchField, StringField, SubmitField,SelectField,SelectMultipleField,IntegerField,RadioField,widgets,BooleanField
from wtforms.validators import DataRequired
import sqlite3
import pandas as pd
import os
import allel
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'f41676960aa9bdaa1122637d89ef298f'

# using path of web application as path of database to avoid error when deploy web app
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "Database/t2d.db")

# Connect to available database
def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn

# create a route for the home page
@app.route("/")
def home():
    return render_template('home.html')

# create a custom multi checkbox field
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

# create form class for summary statistics
class SummaryStatsForm(FlaskForm):
    population = MultiCheckboxField('What population(s) do you want to analyze?',
                                    choices=[('BEB','Bangladeshi'),
                                              ('GIH','Gujarati Indians in Houston'),
                                              ('ITU','Indian Telugu in the UK'),
                                              ('PJL','Pakistani'),
                                              ('all','All')])
    stats_parameter = MultiCheckboxField('Choose parameter(s) for further analysis:',
                                          choices=[('fst','Fst'),
                                                   ('tajimas_d',"Tajima's D"),
                                                   ('all','All')],
                                          )
    calculate_option = BooleanField('Click here if you want to calculate summary statistics\
                                     based on your parameters.',default=False)
    window_size = IntegerField('Window size:',validators=[DataRequired()])
    chromosome_no = StringField('Chromosome:',validators=[DataRequired()])
    start_position = IntegerField('Start position:',validators=[DataRequired()])
    end_position = IntegerField('End position',validators=[DataRequired()])

# define population abbreviation
population_abbr = {'BEB':'Bangladeshi',
                   'GIH':'Gujarati Indians in Houston',
                   'ITU':'Indian Telugu in the UK',
                   'PJL':'Pakistani'}

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

        if search_option == 'SNP_search':
            cursor.execute("""
                SELECT rs_id, location, p_value, ensembl_acc_code FROM snp
                WHERE rs_id LIKE ?
                ORDER BY rs_id
            """, (query,))

            form=None

            results = cursor.fetchall()

        elif search_option == "location_search":   
            try:
                (chromosome,position)=query.split(':')
                (start_position,end_position)=position.split('-')
                cursor.execute("""
                    SELECT rs_id, location, p_value, ensembl_acc_code FROM snp
                    WHERE chromosome = ? and position >= ? and position <= ?
                    ORDER BY position
                """, (chromosome,start_position,end_position))
                
                # Pass the region user searched for to the form
                form=SummaryStatsForm()
                form.chromosome_no.data=chromosome
                form.start_position.data=start_position
                form.end_position.data=end_position
                form.window_size.data=10000
                
                results = cursor.fetchall()

            except:
                # add flash message later
                flash('You have entered invalid genomic coordinate. Please try again!')
                #redirect to home page for user to try again
                return redirect(url_for('home')) 
        
        else:
            cursor.execute("""
                SELECT rs_id, location, p_value, ensembl_acc_code FROM snp 
                WHERE ensembl_acc_code LIKE ?
                ORDER BY ensembl_acc_code
            """, (query,))

            results = cursor.fetchall()

            cursor.execute("""
                SELECT chromosome, start_position, end_position FROM gene 
                WHERE ensembl_acc_code LIKE ?
            """, (query,))
            
            gene_locations = cursor.fetchall()

            if len(gene_locations) == 1:
                (chromosome,start_position,end_position) = gene_locations[0]

                # Pass the genomic location of the gene to the form
                form=SummaryStatsForm()
                form.chromosome_no.data=chromosome
                form.start_position.data=start_position
                form.end_position.data=end_position
                form.window_size.data=10000

            elif len(gene_locations)>1:
                form=SummaryStatsForm()
                form.chromosome_no.data=max([row[0] for row in gene_locations])
                form.start_position.data=min([row[1] for row in gene_locations])
                form.end_position.data=max([row[2] for row in gene_locations])
                form.window_size.data=10000
            
            # if no gene found in the database user have to input the region manually
            # in case user want to calculate summary statistics
            else: 
                form = SummaryStatsForm()
                form.calculate_option.data=True
    
    # add number of results will be displayed and split results into multiple page
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
                           form=form)
    

# create route for gene function page
@app.route('/gene/<gene_name>')
def gene(gene_name):

    # get gene information from database
    conn=get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM gene WHERE ensembl_acc_code = ?""",(gene_name,))
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

# define function to calculate Fst
def calculate_tajimas_d (data,population,start,stop, window_size):
    genotypes = allel.GenotypeArray(data['calldata/GT'])

    # Convert genotype array to allele counts
    allele_counts = genotypes.count_alleles()

    # Get positions
    chromosome_no = data['variants/CHROM'][0]
    positions = data['variants/POS']

    # Compute Tajima's D 

    D, windows, no_base = allel.windowed_tajima_d(pos=positions, ac=allele_counts,start=start,stop=stop, size=window_size)
    start_position_each_interval = [int(x[0]) for x in windows]
    end_position_each_interval = [int(x[1]) for x in windows]
    df = pd.DataFrame(
        {'chromosome':chromosome_no,
        'start_position':start_position_each_interval,
        'end_position':end_position_each_interval,
        f'tajimas_d_{population}':D
        }
    )
    df = df.set_index(['chromosome','start_position','end_position'])

    return df

# define function to plot Tajima's D
def plot_tajimas_d(data_tajima,population):
    plt.figure(figsize=(12, 6))
    # sns.lineplot(x=(data_tajima['start_position']+data_tajima['end_position']-1)//2, y=data_tajima[f'tajimas_d_{pop}'])
    x=(data_tajima['start_position']+data_tajima['end_position']-1)//2
    y=data_tajima[f'tajimas_d_{population}']
    # Plot vertical blue lines for each base pair value
    for x,y in zip(x,y):
            plt.vlines(x, ymin=0, ymax=y, color='blue', alpha=0.6)
    plt.axhline(y=0, color='red', linestyle='--',label="Neutral expectation")
    plt.xlabel("Position (bp)")
    plt.ylabel("Tajima's D")
    plt.title(f"Tajima's D for {population_abbr.get(population)} (Chromosome {data_tajima['chromosome'][0]})")
    plt.legend(loc='upper right')

    # Save plot as image
    plot_path = os.path.join(app_path,'static/plots',f'plot_tajimas_d_{population}.png')
    plt.savefig(plot_path,dpi=500,bbox_inches='tight')
    plt.close()
    

@app.route('/summary-stats-result')
def summary_stats_result():
    population_for_stats=request.args.getlist('population')
    if 'all' in population_for_stats:
        population_for_stats = ['BEB','GIH','ITU','PJL']
    stats_metric=request.args.getlist('stats_parameter')
    if 'all' in stats_metric:
        stats_metric = ['tajimas_d','fst']
    calculate_option = request.args.get('calculate_option',False,type=bool)
    start_position = request.args.get('start_position',type=int)
    end_position = request.args.get('end_position',type=int)
    window_size = request.args.get('window_size',10000,type=int)
    chromosome_no = request.args.get('chromosome_no')
    
    # In case user want to calculate summary statistics by their parameters, read data from vcf files 
    # by required population and save as a dictionary for better performance (to avoid reading vcf files 
    # multiple times if user want to calculate tajima's D and Fst at the same time)
    if calculate_option == True:
        data_by_population={}
        for pop in population_for_stats:
            try:
                print(datetime.datetime.now())
                # pop_samples = list((all_samples[all_samples['population']==pop])['sample_ID'])
                vcf_file_path = os.path.join(app_path,f'Database/vcf_file/{pop}.chr{chromosome_no}.vcf.gz')
                region = f'{chromosome_no}:{start_position}-{end_position}'
                print(region)
                input_data = allel.read_vcf(vcf_file_path,
                                            fields=['variants/CHROM', 'variants/POS', 'calldata/GT'],
                                            region=region)
                
                # handle error if the region users search for is out of range
                if input_data is None:
                    flash(f"You have searched for region {region} which is out of range. Please try again!")
                    return redirect(url_for('sumstats'))
                else:
                    data_by_population[pop]=input_data
            
            # handle error if the chromosome input is not valid
            except FileNotFoundError:
                flash(f'Chromosome "{chromosome_no}" is not valid. Please try again!')
                return redirect(url_for('sumstats'))
    
    #Load or calculate Tajima's D and plot
    if 'tajimas_d' in stats_metric:

        # create text file for summary statistics of Tajima's D
        tajimas_d_file_path = os.path.join(app_path,'static/download/summary_statistics(tajimas_d).txt')
        tajimas_d_file = open(tajimas_d_file_path,'wt')
        tajimas_d_file.write("----- Tajima's D -----\n")

        if calculate_option == False:

            # read data from database
            conn = sqlite3.connect(database_path)
            column_list = [f'tajimas_d_{pop}' for pop in population_for_stats]
            data_tajima=pd.read_sql_query(f"SELECT chromosome, start_position, end_position, {', '.join(column_list)} FROM stats_by_position_interval\
            WHERE chromosome = {chromosome_no} and start_position >= {start_position} and end_position <= {end_position}\
            ORDER BY start_position",conn)
            conn.close

            if data_tajima.empty:
                flash(f"No data found for region {chromosome_no}:{start_position}-{end_position}. Please try again!")
                return redirect(url_for('sumstats'))

            
        if calculate_option == True:

            # calculate Tajima's D based on user input
            print("Processing Tajima's D\t",datetime.datetime.now())

            data_tajima = pd.DataFrame()
            
            for pop in population_for_stats:
                data = data_by_population[pop]
                df_tajimas_d_by_population = calculate_tajimas_d(data, pop, start_position, end_position, window_size)

                # merge data from different populations
                data_tajima = pd.concat([data_tajima,df_tajimas_d_by_population],axis=1)

            data_tajima.reset_index(inplace=True)
        
        # Write Tajima's D data to text file
        tajimas_d_file.write('Population\tAverage\tStandard deviation\n')
        for pop in population_for_stats:
            mean = str(data_tajima[f"tajimas_d_{pop}"].mean())
            std = str(data_tajima[f"tajimas_d_{pop}"].std())
            tajimas_d_file.write(f'{pop} ({population_abbr.get(pop)})\t{mean}\t{std}\n')
        tajimas_d_file.write('\n')
        tajimas_d_file.write(data_tajima.to_string(index=False))
        tajimas_d_file.close()
        
        # Plot Tajima's D for each population
        
        for pop in population_for_stats:
            plot_tajimas_d(data_tajima,pop)

    # Load or calculate Fst
    # if 'fst' in stats_metric:

    return render_template('summary-stats-result.html',
                           population_for_stats=population_for_stats,
                           stats_metric=stats_metric,
                           chromosome_no=chromosome_no,
                           start_position=start_position,
                           end_position=end_position,
                           population_abbr=population_abbr,
                           )

@app.route('/summary_statistics')
def sumstats():

    form = SummaryStatsForm()
    form.calculate_option.data=True # set default value for calculate_option to True when user access the page
    
    return render_template("summary_statistics.html", form=form)

# create route to documentation page
@app.route("/documentation")
def documentation():
    return render_template('documentation.html')

# create route to population about page
@app.route("/about")
def about():
    return render_template('about.html')


app.run(host="0.0.0.0", port=5001) 

# when deploy webapp, using that:
# if __name__ == '__main__':
#     app.run(debug=True)
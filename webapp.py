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
import subprocess


app = Flask(__name__)
app.config['SECRET_KEY'] = 'f41676960aa9bdaa1122637d89ef298f'

# using path of web application as path of database to avoid error when deploy web app
app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "Database/t2d_v3.db")


# Connect to available database
def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn

def last_update_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    last_update_sql = """SELECT MAX(date) FROM accessed;""" # technically this line works since the dates will get bigger each time
    cursor.execute(last_update_sql)
    last_updated = cursor.fetchone()
    last_updated = last_updated[0]
    return last_updated

# create a route for the home page
@app.route("/")
def home():
    last_update = last_update_db()
    return render_template('home.html', last_updated = last_update)

# create a route for updating the database
@app.route("/update_db", methods = ["POST"])
def update_db():
    try:
        subprocess.run(["python", "Database_scripts/database_script.py"], check = True)
    except Exception as e: # if update is unsuccessful error will be returned to the user
        return render_template("home.html", message = "Error updating database", last_updated = last_update_db())
    return redirect(url_for("home"))

# define population abbreviation
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT abbreviation, population FROM populations")
populations=cursor.fetchall()   
conn.close()
population_abbr = {pop[0]:pop[1] for pop in populations}

# define population choices for summary statistics form
populations_for_choices = [(pop[0], pop[1]) for pop in populations if pop[0]!="EUR"]
populations_for_choices.append(("all","All"))

# create a custom multi checkbox field
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


# create form class for summary statistics
class SummaryStatsForm(FlaskForm):
    population = MultiCheckboxField('What population(s) do you want to analyze?',
                                    choices= populations_for_choices)
    stats_parameter = MultiCheckboxField('Choose parameter(s) for summary statistics:',
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
                SELECT a.rs_id, a.location, a.p_value, b.symbol FROM snp a
                INNER JOIN gene b ON a.ensembl_acc_code = b.ensembl_acc_code
                WHERE a.rs_id = ?
                ORDER BY a.rs_id
            """, (query,))

            form=None

            results = cursor.fetchall()

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
                form.window_size.data=10000
                
                results = cursor.fetchall()

            except:
                # add flash message
                flash('You have entered invalid genomic coordinate. Please try again!\
                      Right genomic coordinate format: chromosome:start_position-end_position')
                #redirect to home page for user to try again
                return redirect(url_for('home')) 
        
        else:
            cursor.execute("""
                SELECT a.rs_id, a.location, a.p_value, b.symbol FROM snp a
                INNER JOIN gene b ON a.ensembl_acc_code = b.ensembl_acc_code
                WHERE b.symbol = ?
                ORDER BY a.rs_id
                """, (query,))
            

            results = cursor.fetchall()

            cursor.execute("""
                SELECT chromosome, start_pos, end_pos FROM gene 
                WHERE symbol = ?
            """, (query,))
            
            gene_locations = cursor.fetchall()

            #check these cases again   
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
    
    conn.close()
    
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


# define function to calculate Tajima's D
def calculate_tajimas_d (vcf_data,population,start,stop, window_size):
    genotypes = allel.GenotypeArray(vcf_data['calldata/GT'])

    # Convert genotype array to allele counts
    allele_counts = genotypes.count_alleles()

    # Get positions
    chromosome_no = vcf_data['variants/CHROM'][0]
    positions = vcf_data['variants/POS']

    # Compute Tajima's D and convert to dataframe

    D, windows, no_base = allel.windowed_tajima_d(pos=positions, ac=allele_counts,start=start,stop=stop, size=window_size)
    start_position_each_interval = [int(x[0]) for x in windows]
    end_position_each_interval = [int(x[1]) for x in windows]
    df = pd.DataFrame(
        {'chromosome':chromosome_no,
        'start_position':start_position_each_interval,
        'end_position':end_position_each_interval,
        f'tajimas_d_{population}':D
        })
    
    # set index for dataframe for concatenation tajima's D data from different populations
    df = df.set_index(['chromosome','start_position','end_position'])

    return df


# define function to plot Tajima's D
def plot_tajimas_d(data_tajima,population):
    plt.figure(figsize=(12, 6))
    # sns.lineplot(x=(data_tajima['start_position']+data_tajima['end_position']-1)//2, y=data_tajima[f'tajimas_d_{pop}'])
    x=data_tajima.index # mid position of each window will be used as index later
    y=data_tajima[f'tajimas_d_{population}']

    # Plot vertical blue lines for each base pair value
    plt.vlines(x, ymin=0, ymax=y, color='blue', alpha=0.6)
    plt.axhline(y=0, color='red', linestyle='--',label="Neutral expectation")
    plt.xlabel("Position (bp)")
    plt.ylabel("Tajima's D")
    plt.title(f"Tajima's D for {population_abbr.get(population)} (Chromosome {data_tajima['chromosome'].iloc[0]})")
    plt.legend(loc='upper right')

    # Save plot as image
    plot_path = os.path.join(app_path,'static/plots',f'plot_tajimas_d_{population}.png')
    plt.savefig(plot_path,dpi=500,bbox_inches='tight')
    plt.close()


# define function to calculate Fst
def calculate_fst(vcf_data1,vcf_data2,pop1,pop2,start,stop,window_size):
    genotypes1 = allel.GenotypeArray(vcf_data1['calldata/GT'])
    genotypes2 = allel.GenotypeArray(vcf_data2['calldata/GT'])
    
     # Convert genotype array to allele counts
    allele_counts1 = genotypes1.count_alleles()
    allele_counts2 = genotypes2.count_alleles()
    
    # Get positions
    pos1 = vcf_data1['variants/POS']
    pos2 = vcf_data2['variants/POS']

    # Compute Fst and convert to dataframe
    fst, windows, counts = allel.windowed_hudson_fst(pos1, allele_counts1, allele_counts2, size=window_size,start=start,stop=stop)
    start_position_each_interval = [int(x[0]) for x in windows]
    end_position_each_interval = [int(x[1]) for x in windows]
    df = pd.DataFrame(
        {'chromosome':vcf_data1['variants/CHROM'][0],
        'start_position':start_position_each_interval,
        'end_position':end_position_each_interval,
        f'fst_{pop1}_{pop2}':fst
        })
    
    # set index for dataframe for concatenation Fst data from different populations
    df = df.set_index(['chromosome','start_position','end_position'])

    return df


# define function to plot Fst
def plot_fst(data_fst,pop1,pop2):
    plt.figure(figsize=(12, 6))
    x=data_fst.index # mid position of each window will be used as index later
    y=data_fst[f'fst_{pop1}_{pop2}']
    plt.scatter(x,y, color='blue', s=10, alpha=0.6)
    plt.axhline(y=y.mean(), color='red', linestyle='--',label="Mean")
    plt.xlabel("Position (bp)") 
    plt.ylabel("Fst")
    plt.title(f"Fst between {population_abbr.get(pop1)} and {population_abbr.get(pop2)} (Chromosome {data_fst['chromosome'].iloc[0]})")
    plt.legend(loc='upper right')   
    
    # Save plot as image
    plot_path = os.path.join(app_path,'static/plots',f'plot_fst_{pop1}_{pop2}.png')
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
    chromosome_no = request.args.get('chromosome_no').upper()
    
    # In case user want to calculate summary statistics by their parameters, read data from vcf files 
    # by required population and save as a dictionary for better performance (to avoid reading vcf files 
    # multiple times if user want to calculate tajima's D and Fst at the same time)
    # if calculate_option == True:
    #     data_by_population={}
    #     for pop in population_for_stats:
    #         try:
    #             print(datetime.datetime.now())
    #             # pop_samples = list((all_samples[all_samples['population']==pop])['sample_ID'])
    #             vcf_file_path = os.path.join(app_path,f'Database/vcf_file/{pop}.chr{chromosome_no}.vcf.gz')
    #             region = f'{chromosome_no}:{start_position}-{end_position}'
    #             print(region)
    #             input_data = allel.read_vcf(vcf_file_path,
    #                                         fields=['variants/CHROM', 'variants/POS', 'calldata/GT'],
    #                                         region=region)
                
    #             # handle error if the region users search for is out of range
    #             if input_data is None:
    #                 flash(f"You have searched for region {region} which is out of range. Please try again!")
    #                 return redirect(url_for('sumstats'))
    #             else:
    #                 data_by_population[pop]=input_data
            
    #         # handle error if the chromosome input is not valid
    #         except FileNotFoundError:
    #             flash(f'Chromosome "{chromosome_no}" is not valid. Please try again!')
    #             return redirect(url_for('sumstats'))
    
    # #Load or calculate Tajima's D and plot
    # if 'tajimas_d' in stats_metric:

    #     # create text file for summary statistics of Tajima's D
    #     tajimas_d_file_path = os.path.join(app_path,'static/download/summary_statistics(tajimas_d).txt')
    #     tajimas_d_file = open(tajimas_d_file_path,'wt')
    #     tajimas_d_file.write("----- Tajima's D -----\n")

    #     if calculate_option == False:

    #         # read data from database
    #         conn = sqlite3.connect(database_path)
    #         column_list = [f'tajimas_d_{pop}' for pop in population_for_stats]
    #         data_tajima=pd.read_sql_query(f"SELECT chromosome, start_position, end_position, {', '.join(column_list)} FROM stats_by_position_interval\
    #         WHERE chromosome = {chromosome_no} and start_position >= {start_position} and end_position <= {end_position}\
    #         ORDER BY start_position",conn)
    #         conn.close

    #         if data_tajima.empty:
    #             flash(f"No data found for region {chromosome_no}:{start_position}-{end_position}. Please try again!")
    #             return redirect(url_for('sumstats'))

            
    #     if calculate_option == True:

    #         # calculate Tajima's D based on user input
    #         print("Processing Tajima's D\t",datetime.datetime.now())

    #         data_tajima = pd.DataFrame()
            
    #         for pop in population_for_stats:
    #             data = data_by_population[pop]
    #             df_tajimas_d_by_population = calculate_tajimas_d(data, pop, start_position, end_position, window_size)

    #             # merge data from different populations
    #             data_tajima = pd.concat([data_tajima,df_tajimas_d_by_population],axis=1)

    #         data_tajima.reset_index(inplace=True)
        
    #     # Write Tajima's D data to text file
    #     tajimas_d_file.write('Population\tAverage\tStandard deviation\n')
    #     for pop in population_for_stats:
    #         mean = str(data_tajima[f"tajimas_d_{pop}"].mean())
    #         std = str(data_tajima[f"tajimas_d_{pop}"].std())
    #         tajimas_d_file.write(f'{pop} ({population_abbr.get(pop)})\t{mean}\t{std}\n')
    #     tajimas_d_file.write('\n')tajimas_d
    #     tajimas_d_file.write(data_tajima.to_string(index=False))
    #     tajimas_d_file.close()
        
    #     # Plot Tajima's D for each population
        
    #     for pop in population_for_stats:
    #         plot_tajimas_d(data_tajima,pop)

    # # Load or calculate Fst
    # # if 'fst' in stats_metric:

    if calculate_option == False:
        if 'tajimas_d' in stats_metric:
            # read data from database
            conn = sqlite3.connect(database_path)
            column_list = [f'tajimas_d_{pop}' for pop in population_for_stats]
            data_tajima=pd.read_sql_query(f"""SELECT chromosome, start_position, end_position, {', '.join(column_list)} FROM stats_by_position_interval
            WHERE chromosome = "{chromosome_no}" and start_position >= {start_position-10000} and end_position <= {end_position+10000}
            ORDER BY start_position""",conn,dtype={x:float for x in column_list})
            conn.close()

            if data_tajima.empty:
                flash(f"No data found for region {chromosome_no}:{start_position}-{end_position}. Please try again!")
                return redirect(url_for('sumstats'))
        
        if 'fst' in stats_metric:
            # read data from database
            conn = sqlite3.connect(database_path)
            column_list=[f'fst_{pop}_EUR' for pop in population_for_stats]
            data_fst=pd.read_sql_query(f"""SELECT chromosome, start_position, end_position, {', '.join(column_list)} FROM stats_by_position_interval
            WHERE chromosome = "{chromosome_no}" and start_position >= {start_position-10000} and end_position <= {end_position+10000}
            ORDER BY start_position""",conn,dtype={x:float for x in column_list})
            conn.close()
            

            if data_fst.empty:
                flash(f"No data found for region {chromosome_no}:{start_position}-{end_position}. Please try again!")
                return redirect(url_for('sumstats'))
    
    if calculate_option == True:
        data_tajima = pd.DataFrame()
        data_fst = pd.DataFrame()
        region = f'{chromosome_no}:{start_position}-{end_position}'

        if 'fst' in stats_metric:
            try:
                vcf_EUR_file_path = os.path.join(app_path,f'Database/vcf_file/EUR.chr{chromosome_no}.filtered.vcf.gz')
                vcf_data_EUR = allel.read_vcf(vcf_EUR_file_path,
                                            fields=['variants/CHROM', 'variants/POS', 'calldata/GT'],
                                            region=region)
                # handle error if the region users search for is out of range
                if vcf_data_EUR is None:
                    flash(f"You have searched for region {region} which is out of range. Please try again!")
                    return redirect(url_for('sumstats'))

            # handle error if the chromosome input is not valid
            except FileNotFoundError:
                flash(f'Vcf file for "Chromosome {chromosome_no}" is not found. Please try again!')
                return redirect(url_for('sumstats'))
        
        for pop in population_for_stats:
            try:
                print(datetime.datetime.now())
                # pop_samples = list((all_samples[all_samples['population']==pop])['sample_ID'])
                vcf_file_path = os.path.join(app_path,f'Database/vcf_file/{pop}.chr{chromosome_no}.filtered.vcf.gz')
                vcf_data = allel.read_vcf(vcf_file_path,
                                            fields=['variants/CHROM', 'variants/POS', 'calldata/GT'],
                                            region=region)
                
                # handle error if the region users search for is out of range
                if vcf_data is None:
                    flash(f"You have searched for region {region} which is out of range. Please try again!")
                    return redirect(url_for('sumstats'))

            # handle error if the chromosome input is not valid
            except FileNotFoundError:
                flash(f'Vcf file for "Chromosome {chromosome_no}" is not found. Please try again!')
                return redirect(url_for('sumstats'))

            if 'tajimas_d' in stats_metric:
                
                df_tajimas_d_by_population = calculate_tajimas_d(vcf_data, pop, start_position, end_position, window_size)
                data_tajima = pd.concat([data_tajima,df_tajimas_d_by_population],axis=1)
                # data_tajima.fillna(0,inplace=True)
            
            if 'fst' in stats_metric:
                pop2='EUR'
                df_fst_by_population = calculate_fst(vcf_data,vcf_data_EUR,pop,pop2,start_position,end_position,window_size)
                data_fst = pd.concat([data_fst,df_fst_by_population],axis=1)
                # data_fst.fillna(0,inplace=True)

        data_tajima.reset_index(inplace=True)    
        data_fst.reset_index(inplace=True)

    # Write Tajima's D data to text file and plot 
    if 'tajimas_d' in stats_metric:
        mid_position = (data_tajima['start_position']+data_tajima['end_position'])//2
        data_tajima['mid_position'] = mid_position
        data_tajima.set_index('mid_position',inplace=True)

        tajimas_d_file_path = os.path.join(app_path,'static/download/summary_statistics(tajimas_d).txt')
        tajimas_d_file = open(tajimas_d_file_path,'wt')
        tajimas_d_file.write("----- Tajima's D -----\n")
        tajimas_d_file.write('Population\tAverage\tStandard deviation\n')
        for pop in population_for_stats:

            # Plot Tajima's D for each population
            plot_tajimas_d(data_tajima,pop)

            # Calculate average and standard deviation of Tajima's D for each population and write to text file
            mean = str(data_tajima[f"tajimas_d_{pop}"].mean())
            std = str(data_tajima[f"tajimas_d_{pop}"].std())
            tajimas_d_file.write(f'{pop} ({population_abbr.get(pop)})\t{mean}\t{std}\n')
            
        tajimas_d_file.write('\n')
        tajimas_d_file.write(data_tajima.to_string(index=False))
        tajimas_d_file.close()
        
    
    # Write Fst data to text file and plot 
    if 'fst' in stats_metric:
        mid_position = (data_fst['start_position']+data_fst['end_position'])//2
        data_fst['mid_position'] = mid_position
        data_fst.set_index('mid_position',inplace=True)

        fst_file_path = os.path.join(app_path,'static/download/summary_statistics(fst).txt')
        fst_file = open(fst_file_path,'wt')
        fst_file.write("----- Fst -----\n")
        for pop in population_for_stats:
            fst_file.write(f"{pop}: {population_abbr.get(pop)}\n")

        fst_file.write('Population vs European\tAverage\tStandard deviation\n')
        pop2 = 'EUR'

        for pop in population_for_stats:
            # Plot Fst between each pair of populations
            plot_fst(data_fst,pop,pop2)

            # Calculate average and standard deviation of Fst between each pair of populations and write to text file
            mean = str(data_fst[f"fst_{pop}_{pop2}"].mean())
            std = str(data_fst[f"fst_{pop}_{pop2}"].std())
            fst_file.write(f'Fst_{pop}_{pop2}\t{mean}\t{std}\n')

        fst_file.write('\n')
        fst_file.write(data_fst.to_string(index=False))
        fst_file.close()

    return render_template('summary-stats-result.html',
                           population_for_stats=population_for_stats,
                           stats_metric=stats_metric,
                           chromosome_no=chromosome_no,
                           start_position=start_position,
                           end_position=end_position,
                           population_abbr=population_abbr,)


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


# app.run(host="0.0.0.0", port=5000) 

# when deploy webapp, using that:
if __name__ == '__main__':
    app.run(debug=True)
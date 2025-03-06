import allel
import numpy as np
import pandas as pd
import datetime
import sqlite3
import os

app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "./Database/t2d_snp_portal.db")

conn=sqlite3.connect(database_path)
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS stats_by_position_interval')

cursor.execute("""CREATE TABLE stats_by_position_interval (chromosome varchar(2),start_position int, end_position int,
                    tajimas_d_BEB float, tajimas_d_GIH float, tajimas_d_ITU float, tajimas_d_PJL float,
                    fst_BEB_EUR float, fst_GIH_EUR float, fst_ITU_EUR float, fst_PJL_EUR float)""")
cursor.execute('CREATE INDEX stats_by_position_interval_index ON stats_by_position_interval (chromosome, start_position, end_position)')
conn.commit()
conn.close()

populations = ['BEB','GIH','ITU','PJL']
window_size = 10000
df_stats = pd.DataFrame()
all_vcf_data = {}

def calculate_fst(chromosome,vcf_data1,vcf_data2,pop1,pop2,window_size):
    genotypes1 = allel.GenotypeArray(vcf_data1['calldata/GT'])
    genotypes2 = allel.GenotypeArray(vcf_data2['calldata/GT'])
    allele_counts1 = genotypes1.count_alleles()
    allele_counts2 = genotypes2.count_alleles()
    pos1 = vcf_data1['variants/POS']
    pos2 = vcf_data2['variants/POS']
    fst, windows, counts = allel.windowed_hudson_fst(pos1, allele_counts1, allele_counts2, size=window_size,start=1)
    start_position_each_interval = [int(x[0]) for x in windows]
    end_position_each_interval = [int(x[1]) for x in windows]
    df = pd.DataFrame(
        {'chromosome':chromosome,
        'start_position':start_position_each_interval,
        'end_position':end_position_each_interval,
        f'fst_{pop1}_{pop2}':fst
        }
    )
    df = df.set_index(['chromosome','start_position','end_position'])
    return df

def vcf_file_path(population,chromosome):
    return os.path.join(app_path,f'../Database/vcf_file/{population}.chr{chromosome}.filtered.vcf.gz')

# for chromosome in list(range(1,23))+['X']:
for chromosome in range(1,2):
    vcf_data_EUR = allel.read_vcf(vcf_file_path('EUR',chromosome), 
                              fields=['variants/CHROM','variants/POS','calldata/GT'])

    df_chromosome=pd.DataFrame()
    
    for population in populations:
        
        print(f'{population} processing chromosome {chromosome}', datetime.datetime.now())
        vcf_data = allel.read_vcf(vcf_file_path(population,chromosome),  
                              fields=['variants/CHROM','variants/POS','calldata/GT'])
        # all_vcf_data[population] = vcf_data


        genotypes = allel.GenotypeArray(vcf_data['calldata/GT'])
        ac = genotypes.count_alleles()
        position = vcf_data['variants/POS']

        D, windows, no_base = allel.windowed_tajima_d(pos=position,
                                                      ac=ac,
                                                      size=window_size,
                                                      start=1)
        start_position=[int(x[0]) for x in windows]
        end_position=[int(x[1]) for x in windows]
        df = pd.DataFrame(
            {'chromosome':chromosome,
             'start_position':start_position,
                'end_position':end_position,
                f'tajimas_d_{population}':D
            }
        )
        df = df.set_index(['chromosome','start_position','end_position'])
        # df.fillna(0,inplace=True)
        df_chromosome= pd.concat([df_chromosome,df],axis=1)
        print(f'{population} finishing Tajima D chromosome {chromosome}', datetime.datetime.now())

        pop2 = 'EUR'
        df_fst = calculate_fst(chromosome,vcf_data,vcf_data_EUR,population,pop2,window_size)
        # df_fst.fillna(0,inplace=True)
        df_chromosome = pd.concat([df_chromosome,df_fst],axis=1)
        print(f'finish Fst_{population}_{pop2}', datetime.datetime.now())

    df_chromosome.reset_index(inplace=True)
    conn=sqlite3.connect(database_path)
    df_chromosome.to_sql('stats_by_position_interval',conn,if_exists='append',index=False)
    conn.close
    
#     df_stats=pd.concat([df_stats,df_chromosome],axis=0)


# df_stats.to_csv('stats_result.tsv',sep='\t')
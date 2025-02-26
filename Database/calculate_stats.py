import allel
import numpy as np
import pandas as pd
import matplotlib as plt
import datetime

window_size = 10000
df_tajima = pd.DataFrame()
for population in ['BEB','GIH']:
    df_pop=pd.DataFrame()
    for chromosome in range (1,3):
        print(f'{population} processing chromosome {chromosome}', datetime.datetime.now())
        data = allel.read_vcf(f'vcf_file/{population}.chr{chromosome}.vcf.gz', 
                              fields=['variants/CHROM','variants/POS','calldata/GT'])
        genotypes = allel.GenotypeArray(data['calldata/GT'])
        ac = genotypes.count_alleles()
        position = data['variants/POS']

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
        df.fillna(0,inplace=True)
        df_pop= pd.concat([df_pop,df],axis=0)
        print(f'{population} finishing chromosome {chromosome}', datetime.datetime.now())

    df_tajima=pd.concat([df_tajima,df_pop],axis=1)
    
        
df_tajima.to_csv('tajima_result.tsv',sep='\t')
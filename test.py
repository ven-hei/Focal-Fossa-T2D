# import allel
# import numpy as np
# import matplotlib.pyplot as plt
# import os

# vcf_dir = "/Users/zhou/Download/ITU_population"
# population = "ITU"

# def calculate_tajima_d(vcf_path, window_size=100000, step_size=50000):
#     callset = allel.read_vcf(vcf_path, fields=['variants/POS', 'calldata/GT'])
#     gt = allel.GenotypeArray(callset['calldata/GT'])
#     pos = callset['variants/POS']
#     ac = gt.count_alleles()
#     tajima_d, windows, counts = allel.windowed_tajima_d(
#     pos=pos,
#     ac=ac,
#     size=window_size,
#     step=step_size,
#     )
#     return tajima_d, windows, pos

# def plot_tajima_d(tajima_d, windows, chromosome):
#     plt.figure(figsize=(12, 6))
#     window_midpoints = (windows[:, 0] + windows[:, 1]) // 2
#     plt.plot(window_midpoints, tajima_d, label=f"Chromosome {chromosome}")
#     plt.axhline(0, color='red', linestyle='--', label="Neutral expectation")
#     plt.title(f"Tajima's D for {population} (Chromosome {chromosome})")
#     plt.xlabel("Position (bp)")
#     plt.ylabel("Tajima's D")
#     plt.legend()
#     plt.savefig(f"tajima_d_chr{chromosome}.png")
#     plt.close()

# for chrom in range(1, 22):
#     vcf_path = os.path.join(vcf_dir, f"{population}.chr{chrom}.vcf.gz")
#     if not os.path.exists(vcf_path):
#         print(f"Skipping chromosome {chrom} (file not found)")
#     continue
#     print(f"Processing chromosome {chrom}...")
#     try:
#         tajima_d, windows, pos = calculate_tajima_d(vcf_path)
#         plot_tajima_d(tajima_d, windows, chrom)
#         print(f"Plot saved for chr{chrom}")
#     except Exception as e:
#         print(f"Error on chr{chrom}: {str(e)}")

# print("Done")

import os
import sqlite3

gene_name = input("Enter gene name: ")

app_path = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(app_path, "Database/t2d.db")

def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn

conn=get_db_connection()
cursor = conn.cursor()
cursor.execute("""SELECT * FROM gene WHERE ensembl_acc_code = ?""",(gene_name,))
gene_info = cursor.fetchone()
gene_info = list(gene_info)
conn.close()

if gene_info[2]:
    a=list(gene_info[2].split(". "))
    gene_info[2] = '.\n\t- '.join(a)
    gene_info=tuple(gene_info)

print(gene_info[2])
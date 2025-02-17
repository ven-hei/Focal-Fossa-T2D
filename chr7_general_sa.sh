#!/bin/bash
#$ -cwd
#$ -l h_rt=2:00:00
#$ -l h_vmem=8G
#$ -pe smp 4
#$ -m bea
#$ -N filter_t2d_south_asian

module load bcftools

bcftools view -S south_asian_samples.txt -o subset_chr7_south_asian.vcf.gz annotated_chr7.vcf.gz

cut -d ',' -f21 snp_sa_id.csv | sed '1d; s/"//g' | sort | uniq > t2d_snp_ids.txt

bcftools view -T t2d_snp_ids.txt -o filtered_chr7_t2d_south_asian.vcf.gz subset_chr7_south_asian.vcf.gz

bcftools stats filtered_chr7_t2d_south_asian.vcf.gz > chr7_t2d_south_asian_summary_stats.txt


import os
import flask
import allel
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, send_file

base_data_dir = "/Users/hananabdi/Downloads"  # Base directory containing population folders

app = Flask(__name__, template_folder="templates")  # Ensure Flask looks in the right folder

# Load VCF data function
def load_vcf_data(population, chromosome):
    # Updated folder naming: using "filtered_{population}"
    data_dir = os.path.join(base_data_dir, f"filtered_{population}")
    # Updated file format with ".filtered" added before the extension
    vcf_file = os.path.join(data_dir, f"{population}.chr{chromosome.replace('chr', '')}.filtered.vcf.gz")
    
    print(f"Looking for file: {vcf_file}")
    if not os.path.exists(vcf_file):
        print("File not found!")
        return f"Error: File {vcf_file} not found"
    
    try:
        callset = allel.read_vcf(vcf_file)
        return callset
    except Exception as e:
        print(f"Error reading VCF: {e}")
        return str(e)

# Tajima's D calculation
def calculate_tajima_d(vcf_path, window_size=50000, step_size=50000):
    print(f"➡ Starting Tajima's D Calculation: {vcf_path}, Window: {window_size}, Step: {step_size}")
    try:
        callset = allel.read_vcf(vcf_path, fields=['variants/POS', 'calldata/GT'])
        gt = allel.GenotypeArray(callset['calldata/GT'])
        pos = callset['variants/POS'][:10000]  # Limit to first 10,000 positions
        ac = gt.count_alleles()[:10000]
        
        tajima_d, windows, counts = allel.windowed_tajima_d(
            pos=pos,
            ac=ac,
            size=window_size,
            step=step_size,
        )
        
        tajima_d = np.where(tajima_d.size > 0, tajima_d, np.array([0]))
        print(f"✅ Tajima's D Computed: {len(tajima_d)} values")
        return tajima_d, windows, pos

    except Exception as e:
        print(f"❌ Error in Tajima's D Calculation: {e}")
        return str(e)

def plot_tajima_d(tajima_d, windows, chromosome, population):
    import matplotlib
    matplotlib.use("Agg")  # Use non-GUI backend
    import matplotlib.pyplot as plt
    import os

    # Ensure static/plots directory exists
    plot_dir = "static/plots"
    os.makedirs(plot_dir, exist_ok=True)

    plt.figure(figsize=(12, 6))

    # Plot vertical blue lines for each base pair value
    for x, y in zip(windows[:, 0], tajima_d):  
        plt.vlines(x, ymin=0, ymax=y, color='blue', alpha=0.6)

    plt.axhline(0, color='red', linestyle='--', label="Neutral expectation")

    plt.title(f"Tajima's D for {population} (Chromosome {chromosome})")
    plt.xlabel("Base Pair Position (bp)")
    plt.ylabel("Tajima's D")
    plt.legend()

    # Save the plot
    plot_path = os.path.join(plot_dir, f"tajima_d_chr{chromosome}_{population}.png")
    plt.savefig(plot_path)
    plt.close()

    print(f"✅ Plot saved at: {plot_path}")
    return plot_path

def calculate_fst_for_rs(population, chromosome, rs_list, window_size=50000):
    try:
        import matplotlib
        matplotlib.use("Agg")  # Use non-GUI backend
        import matplotlib.pyplot as plt
        import os

        # Load VCF data for both the selected population and European (EUR)
        pop_vcf = load_vcf_data(population, chromosome)
        eur_vcf = load_vcf_data("EUR", chromosome)

        if isinstance(pop_vcf, str) or isinstance(eur_vcf, str):
            return f"Error loading VCF files for {population} or EUR."

        # Extract rs IDs and SNP positions
        pop_rs_ids = pop_vcf['variants/ID']
        eur_rs_ids = eur_vcf['variants/ID']
        pop_pos = pop_vcf['variants/POS']
        eur_pos = eur_vcf['variants/POS']

        # Filter only user-selected rs numbers
        mask_pop = np.isin(pop_rs_ids, rs_list)
        mask_eur = np.isin(eur_rs_ids, rs_list)

        if not np.any(mask_pop) or not np.any(mask_eur):
            return "Error: Selected rs numbers not found in both populations."

        # Subset VCF data for the selected rs IDs
        pop_filtered = {key: value[mask_pop] for key, value in pop_vcf.items()}
        eur_filtered = {key: value[mask_eur] for key, value in eur_vcf.items()}

        # Align SNP positions using intersection indices
        common_positions, idx_pop, idx_eur = np.intersect1d(
            pop_filtered['variants/POS'], eur_filtered['variants/POS'], return_indices=True
        )

        if common_positions.size == 0:
            return "Error: No common positions found for selected rs numbers."

        # Extract allele counts for the matched SNPs
        pop_gt = allel.GenotypeArray(pop_filtered['calldata/GT'])[idx_pop]
        eur_gt = allel.GenotypeArray(eur_filtered['calldata/GT'])[idx_eur]

        pop_ac = pop_gt.count_alleles()
        eur_ac = eur_gt.count_alleles()

        # Compute windowed Fst
        fst_values, fst_windows, _ = allel.windowed_weir_cockerham_fst(
            pos=common_positions,
            ac1=pop_ac,
            ac2=eur_ac,
            size=window_size
        )

        if len(fst_values) == 0:
            return "Error: No Fst values computed for selected rs numbers."

        # Plot Fst values
        plot_dir = "static/plots"
        os.makedirs(plot_dir, exist_ok=True)

        plt.figure(figsize=(12, 6))
        plt.plot(common_positions, fst_values, color='blue', linestyle='-', marker='o', markersize=4, label="Fst")
        plt.axhline(0, color='red', linestyle='--', label="Neutral expectation")
        plt.title(f"Fst for {population} vs EUR (Selected rs Numbers)")
        plt.xlabel("Position (bp)")
        plt.ylabel("Fst")
        plt.legend()

        plot_path = os.path.join(plot_dir, f"fst_rs_{population}.png")
        plt.savefig(plot_path)
        plt.close()

        return plot_path  # Only returning the plot, not the Fst values

    except Exception as e:
        return f"❌ Error in Fst Calculation: {e}"

def calculate_fst_for_region(population, chromosome, window_size=50000, position_start=None, position_end=None):
    try:
        import matplotlib
        matplotlib.use("Agg")  # Use non-GUI backend
        import matplotlib.pyplot as plt
        import os

        # Load VCF data for both the selected population and European (EUR)
        pop_vcf = load_vcf_data(population, chromosome)
        eur_vcf = load_vcf_data("EUR", chromosome)

        if isinstance(pop_vcf, str) or isinstance(eur_vcf, str):
            return f"Error loading VCF files for {population} or EUR."

        # Extract SNP positions
        pop_pos = pop_vcf['variants/POS']
        eur_pos = eur_vcf['variants/POS']

        # If a region is provided, filter both VCF callsets by that region.
        if position_start is not None and position_end is not None:
            pos_start = int(position_start)
            pos_end = int(position_end)
            pop_region_mask = (pop_pos >= pos_start) & (pop_pos <= pos_end)
            eur_region_mask = (eur_pos >= pos_start) & (eur_pos <= pos_end)

            # Apply filtering to SNP positions
            pop_pos = pop_pos[pop_region_mask]
            eur_pos = eur_pos[eur_region_mask]

        # Align SNP positions using intersection indices
        common_positions, idx_pop, idx_eur = np.intersect1d(pop_pos, eur_pos, return_indices=True)

        if common_positions.size == 0:
            return "Error: No common positions found between populations."

        # Extract genotype arrays
        pop_gt = allel.GenotypeArray(pop_vcf['calldata/GT'])[idx_pop]
        eur_gt = allel.GenotypeArray(eur_vcf['calldata/GT'])[idx_eur]

        pop_ac = pop_gt.count_alleles()
        eur_ac = eur_gt.count_alleles()

        # ✅ Corrected function call (NO named arguments)
        fst_values, fst_windows, _ = allel.windowed_weir_cockerham_fst(common_positions, pop_ac, eur_ac, window_size)

        # Plot Fst values
        plot_dir = "static/plots"
        os.makedirs(plot_dir, exist_ok=True)

        plt.figure(figsize=(12, 6))
        plt.plot(common_positions, fst_values, color='blue', linestyle='-', marker='o', markersize=4, label="Fst")
        plt.axhline(0, color='red', linestyle='--', label="Neutral expectation")
        plt.title(f"Fst for {population} vs EUR (Genomic Region)")
        plt.xlabel("Position (bp)")
        plt.ylabel("Fst")
        plt.legend()

        plot_path = os.path.join(plot_dir, f"fst_region_{population}.png")
        plt.savefig(plot_path)
        plt.close()

        return plot_path

    except Exception as e:
        return f"❌ Error in Fst Calculation: {e}"




# Homepage route
@app.route("/")
def home():
    return render_template("base.html")

# Summary statistics page
@app.route("/summary_statistics")
def summary_statistics():
    return render_template("summary_statistics.html")

# Documentation page
@app.route("/documentations")
def documentations():
    return render_template("documentations.html")

# About page
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/summary_stats_result")
def summary_stats_result():
    population = request.args.getlist("population")
    chromosome = request.args.get("chromosome", "22")
    parameters = request.args.getlist("parameter")
    rs_numbers = request.args.get("rs_numbers")  # Get user-selected rs numbers
    position_start = request.args.get("position_start")  # Get genomic region start
    position_end = request.args.get("position_end")  # Get genomic region end
    window_size = int(request.args.get("window_size", 100000))

    results = {}

    # Convert RS numbers into a list (if provided)
    rs_list = [rs.strip() for rs in rs_numbers.split(",") if rs.strip()] if rs_numbers else []

    for pop in population:
        callset = load_vcf_data(pop, chromosome)
        if isinstance(callset, str):
            results[pop] = {"Error": callset}
            continue

        results[pop] = {}

        ### **🔹 Add Tajima's D Calculation**
        if "Tajima D" in parameters:
            vcf_file = os.path.join(base_data_dir, f"filtered_{pop}", f"{pop}.chr{chromosome.lstrip('chr')}.filtered.vcf.gz")
            tajima_d_values, windows, _ = calculate_tajima_d(vcf_file, window_size=window_size)
            plot_path = plot_tajima_d(tajima_d_values, windows, chromosome, pop)
            results[pop]["Tajima_Plot"] = plot_path  # Store the plot path

        ### **🔹 Add Fst Calculation**
        if "Fst" in parameters:
            if rs_list:
                # Calculate Fst for user-selected rs numbers
                results[pop]["Fst_Plot"] = calculate_fst_for_rs(pop, chromosome, rs_list, window_size=window_size)
            elif position_start and position_end:
                # Calculate Fst for a genomic region
                results[pop]["Fst_Plot"] = calculate_fst_for_region(pop, chromosome, window_size=window_size, 
                                                                    position_start=position_start, position_end=position_end)
            else:
                results[pop]["Fst"] = "Error: No rs numbers or genomic region selected for Fst calculation."

    return render_template("summary-stats-result.html", results=results)



# Download summary statistics
@app.route("/download_summary")
def download_summary():
    file_path = os.path.join(base_data_dir, "summary_statistics.csv")
    if not os.path.exists(file_path):
        return "Summary statistics file not found.", 404
    return send_file(file_path, as_attachment=True)


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)

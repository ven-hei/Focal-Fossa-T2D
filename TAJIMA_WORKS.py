import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import io
from flask import Flask, render_template, request, send_file
import json
matplotlib.use('Agg')  # ✅ Ensure Matplotlib runs in non-GUI mode

app = Flask(__name__, template_folder="templates")

# Load precomputed min start positions
with open("min_start_positions.json") as f:
    CHROM_POP_MIN_STARTS = json.load(f)

# ✅ Path to SQLite Database
DATABASE_PATH = "/Users/hananabdi/Desktop/Focal-Fossa-T2D/Database/stats.db"

# ✅ Database Connection
def get_db_connection():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enables column access by name
    return conn

def load_tajima_d_data(populations, chromosome, start_position=None, end_position=None):
    """Load Tajima's D data from SQLite for multiple populations, ensuring each has its correct min start position within the user-selected region."""

    chrom_num = int(str(chromosome).replace("chr", "").strip())  # ✅ Ensure valid chromosome format

    # ✅ Ensure population names match the database column names
    population_column_map = {
        "BEB": "tajima_d_BEB",
        "ITU": "tajima_d_ITU",
        "GIH": "tajima_d_GIH",
        "PJL": "tajima_d_PJL"
    }

    # ✅ Filter only valid populations
    selected_columns = {pop: population_column_map[pop] for pop in populations if pop in population_column_map}

    if not selected_columns:
        print(f"❌ No valid populations found in request: {populations}")
        return {}, [], "No valid populations selected"

    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Find minimum start positions per population
    min_start_positions = {}
    for pop, col in selected_columns.items():
        cursor.execute(f"SELECT MIN(start_position) FROM tajima_d WHERE chromosome = ? AND {col} IS NOT NULL", (chrom_num,))
        min_pos = cursor.fetchone()[0]
        min_start_positions[pop] = min_pos if min_pos is not None else None

    conn.close()

    # ✅ Adjust genomic region based on user input and per-population min_start
    adjusted_ranges = {}
    for pop, min_pos in min_start_positions.items():
        if min_pos is None:
            adjusted_ranges[pop] = "No SNPs available"
            continue

        adj_start = max(min_pos, start_position) if isinstance(start_position, int) else min_pos
        adj_end = end_position if isinstance(end_position, int) else (adj_start + 1_000_000)

        adjusted_ranges[pop] = (adj_start, adj_end) if adj_end > adj_start else "No SNPs available"

    # ✅ Fetch SNP data per population using the correctly adjusted range
    results = {}
    conn = get_db_connection()
    cursor = conn.cursor()

    for pop, col in selected_columns.items():
        if adjusted_ranges[pop] == "No SNPs available":
            results[pop] = {
                "Tajima_D": [np.nan],
                "Positions": [np.nan],
                "Range": "No SNPs available"
            }
            continue

        adj_start, adj_end = adjusted_ranges[pop]
        cursor.execute(f"""
            SELECT start_position, {col}
            FROM tajima_d
            WHERE chromosome = ? AND {col} IS NOT NULL AND start_position BETWEEN ? AND ?
        """, (chrom_num, adj_start, adj_end))
        rows = cursor.fetchall()

        if not rows:
            results[pop] = {
                "Tajima_D": [np.nan],
                "Positions": [np.nan],
                "Range": "No SNPs available"
            }
            continue

        df = pd.DataFrame(rows, columns=["start_position", col]).dropna()
        results[pop] = {
            "Tajima_D": df[col].tolist(),
            "Positions": df["start_position"].tolist(),
            "Range": f"{adj_start} - {adj_end}"
        }

    conn.close()
    return results, list(results.keys()), "Valid SNPs found"


# ✅ Function to plot Tajima's D
def plot_tajima_d(tajima_d, windows, chromosome, population):
    """Generates a Tajima's D scatter plot."""
    if tajima_d is None or len(tajima_d) == 0:
        print(f"❌ No Tajima's D values for {population} (Chromosome {chromosome})")
        return None  # Exit early if no valid data

    plt.figure(figsize=(12, 6))

    # ✅ Scatter plot
    plt.scatter(windows[:, 0], tajima_d, color='blue', s=10, label="Tajima's D (Scatter)")
    plt.axhline(0, color='red', linestyle="--", label="Neutral expectation")

    plt.title(f"Tajima's D for {population} (Chromosome {chromosome})")
    plt.xlabel("Genomic Position (bp)")
    plt.ylabel("Tajima's D")
    plt.legend()
    plt.ylim(np.nanmin(tajima_d) - 0.8, np.nanmax(tajima_d) + 0.8)

    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png', dpi=300)  # ✅ Save plot to image buffer
    plt.close()  # ✅ Prevent memory leaks
    img_stream.seek(0)

    return img_stream



def load_fst_data(chromosome, start_position, end_position, populations):
    """Fetches FST values for the selected chromosome, genomic region, and multiple populations."""

    chrom_num = int(chromosome.replace("chr", "").strip())  # Ensure chromosome is an integer
    conn = sqlite3.connect("/Users/hananabdi/Desktop/Focal-Fossa-T2D/Database/stats.db")
    cursor = conn.cursor()

    # ✅ Map population selections to database column names
    population_column_map = {
        "BEB": "fst_EUR_BEB",
        "ITU": "fst_EUR_ITU",
        "GIH": "fst_EUR_GIH",
        "PJL": "fst_EUR_PJL"
    }

    # ✅ Filter only valid populations
    selected_columns = {pop: population_column_map[pop] for pop in populations if pop in population_column_map}

    if not selected_columns:
        print(f"❌ No valid populations found in request: {populations}")
        return {}, [], "No valid populations selected"

    # ✅ Dynamically create SQL query with selected columns
    selected_col_names = ", ".join(selected_columns.values())  # e.g., "fst_EUR_BEB, fst_EUR_ITU"
    query = f"""
    SELECT start_position, {selected_col_names}
    FROM fst
    WHERE chromosome = ? AND start_position BETWEEN ? AND ?
    """

    try:
        cursor.execute(query, (chrom_num, start_position, end_position))
        rows = cursor.fetchall()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"❌ SQLite Error: {e}")  # Debugging output
        return {}, [], "Database Error"

    if not rows:
        print(f"❌ No FST data found for Chromosome {chrom_num} in range {start_position} - {end_position}")
        return {}, [], "No FST values available"

    # ✅ Convert to DataFrame
    column_names = ["Position"] + list(selected_columns.keys())  # Example: ["Position", "BEB", "ITU"]
    df = pd.DataFrame(rows, columns=column_names).dropna()

    # ✅ Organize FST values per population
    results = {}
    for pop in selected_columns.keys():
        results[pop] = {
            "FST_Values": df[pop].values.tolist(),
            "Positions": df["Position"].values.tolist(),
            "Range": f"{start_position} - {end_position}"
        }

    return results, list(results.keys()), "Valid FST data found"
def plot_fst(fst_values, positions, chromosome, population):
    """Generates an FST scatter plot for a given chromosome region and population."""
    if fst_values is None or len(fst_values) == 0:
        print(f"❌ No FST values for {population} (Chromosome {chromosome})")
        return None  # Exit early if no valid data

    plt.figure(figsize=(12, 6))
    
    # ✅ Scatter plot of all FST values for the selected population
    plt.scatter(positions, fst_values, color='blue', s=10, label=f"FST Values ({population})")

    # ✅ Compute and plot the average FST value for the selected region
    avg_fst = np.nanmean(fst_values)
    plt.axhline(avg_fst, color='red', linestyle="--", label=f"Avg FST = {avg_fst:.4f}")

    plt.title(f"FST for {population} (Chromosome {chromosome})")
    plt.xlabel("Genomic Position (bp)")
    plt.ylabel("FST Value")
    plt.legend()
    plt.ylim(np.nanmin(fst_values) - 0.05, np.nanmax(fst_values) + 0.05)

    img_stream = io.BytesIO()
    plot_filename = f"static/fst_{population}_chr{chromosome}.png"  # ✅ Unique filename per population
    plt.savefig(plot_filename, format='png', dpi=300)
    plt.close()  # ✅ Prevent memory leaks

    return plot_filename


# ✅ Flask Routes
@app.route("/")
def home():
    return render_template("base.html")

@app.route("/summary_statistics")
def summary_statistics():
    return render_template("summary_statistics.html")

@app.route("/documentations")
def documentations():
    return render_template("documentations.html")

@app.route("/about")
def about():
    return render_template("about.html")



@app.route("/summary_stats_result")
def summary_stats_result():
    """Handles user request for FST and Tajima's D based on genomic region input."""

    test_type = request.args.get("test_type", "").lower()
    chromosome = request.args.get("chromosome", "").replace("chr", "").strip()

    # ✅ Ensure chromosome is numeric (1-22)
    if not chromosome.isdigit():
        return "Error: Invalid chromosome input. Please enter a valid chromosome number (1-22).", 400

    def clean_input(value, default=None):
        if value is None:
            return default
        cleaned_value = value.replace(",", "")
        return int(cleaned_value) if cleaned_value.isdigit() else default

    user_start = clean_input(request.args.get("position_start"))
    end_position = clean_input(request.args.get("position_end"))
    window_size = clean_input(request.args.get("window_size"), 10000)  # Default 10,000

    if not chromosome:
        return "Error: Please select a chromosome.", 400

    # ✅ Processing FST
    if test_type == "fst":
        populations = request.args.getlist("population")  # ✅ Handles multiple populations

        if not populations:
            return "Error: No valid populations selected.", 400

        # ✅ Load FST data for selected populations
        results, valid_populations, status_message = load_fst_data(chromosome, user_start, end_position, populations)

        if not valid_populations:
            return f"Error: {status_message}", 400

        # ✅ Generate FST plots for each population
        plot_paths = {}
        for pop in valid_populations:
            plot_path = plot_fst(results[pop]["FST_Values"], results[pop]["Positions"], chromosome, pop)
            if plot_path:
                plot_paths[pop] = plot_path

        return render_template(
            "summary_stats_result.html",
            test_type="fst",
            plot_paths=plot_paths,
            selected_chromosome=chromosome
        )

    # ✅ Processing Tajima's D
    elif test_type == "tajima":
        populations = request.args.getlist("population")  # ✅ Handles multiple populations

        if not populations:
            return "Error: No valid populations selected.", 400

        # ✅ Load Tajima's D data for all selected populations
        results, valid_populations, status_message = load_tajima_d_data(populations, chromosome, user_start, end_position)

        if not valid_populations:
            return f"Error: {status_message}", 400  # Handle case where no populations have valid data

        final_results = {}

        for population in valid_populations:
            tajima_d_values = results[population]["Tajima_D"]
            positions = results[population]["Positions"]
            available_range = results[population]["Range"]

            if tajima_d_values is None or len(tajima_d_values) == 0:
                final_results[population] = {
                    "Error": f"Tajima's D data not found for {population}",
                    "Available_Range": available_range
                }
                continue

            # ✅ Apply windowing for Tajima's D
            positions_array = np.array(positions)
            tajima_d_array = np.array(tajima_d_values)

            window_starts = np.arange(positions_array.min(), positions_array.max(), window_size)
            window_ends = window_starts + window_size
            windows = np.column_stack((window_starts, window_ends))

            windowed_tajima_d = []
            for start, end in zip(window_starts, window_ends):
                mask = (positions_array >= start) & (positions_array < end)
                if np.any(mask):
                    windowed_tajima_d.append(np.nanmean(tajima_d_array[mask]))
                else:
                    windowed_tajima_d.append(np.nan)

            # ✅ Generate Tajima's D plot
            tajima_plot = plot_tajima_d(np.array(windowed_tajima_d), windows, chromosome, population)
            plot_path = f"static/tajima_{population}_chr{chromosome}_win{window_size}.png"

            if tajima_plot is not None:
                with open(plot_path, "wb") as f:
                    f.write(tajima_plot.getbuffer())
                final_results[population] = {
                    "Tajima_Plot": plot_path,
                    "Available_Range": available_range
                }
            else:
                final_results[population] = {
                    "Error": f"No valid Tajima's D plot for {population}",
                    "Available_Range": available_range
                }

        return render_template(
            "summary_stats_result.html",
            results=final_results,
            selected_chromosome=chromosome,
        )

    else:
        return "Error: Invalid test type. Please select 'fst' or 'tajima'.", 400

# ✅ Run Flask App
if __name__ == "__main__":
    app.run(debug=True)

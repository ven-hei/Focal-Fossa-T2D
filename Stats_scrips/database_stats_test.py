import sqlite3
import os

# Path to your database
db_path = "/Users/hananabdi/Desktop/Focal-Fossa-T2D/focal_fossa.db"

# Path to your data folder
data_folder = "/Users/hananabdi/Desktop/Focal-Fossa-T2D/"

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Debugging: Check available files
print("Checking files in:", data_folder)
available_files = os.listdir(data_folder)
print("Files found:", available_files)

# Identify FST and Tajima.D files
fst_files = [f for f in available_files if f.endswith(".fst") and "chr" in f]
tajima_files = [f for f in available_files if f.endswith(".Tajima.D") and "chr" in f]

if not fst_files and not tajima_files:
    print("No relevant files found. Check your filenames and path.")
    conn.close()
    exit()

# Define column mapping for FST and Tajima's D tables
fst_column_mapping = {
    "BEB": "fst_EUR_BEB",
    "ITU": "fst_EUR_ITU",
    "GIH": "fst_EUR_GIH",
    "PJL": "fst_EUR_PJL",
}

tajima_column_mapping = {
    "BEB": "tajima_d_BEB",
    "ITU": "tajima_d_ITU",
    "GIH": "tajima_d_GIH",
    "PJL": "tajima_d_PJL",
}

# Function to insert data into the fst table
def insert_fst_data(file_path, chromosome, fst_column):
    with open(file_path, 'r') as file:
        next(file)  # Skip header row
        for line in file:
            columns = line.strip().split()  # Assuming tab-separated
            if len(columns) < 3:
                continue  # Skip invalid rows

            start_position = int(columns[1])  # POS column
            fst_value = float(columns[2])  # WEIR_AND_COCKERHAM_FST column

            # Debugging print statement
            print(f"Inserting: chromosome={chromosome}, start_position={start_position}, {fst_column}={fst_value}")

            # Use UPSERT to prevent duplicates
            cursor.execute(
                f"""INSERT INTO fst (chromosome, start_position, {fst_column})
                VALUES (?, ?, ?)
                ON CONFLICT(chromosome, start_position)
                DO UPDATE SET {fst_column} = excluded.{fst_column};""",
                (chromosome, start_position, fst_value),
            )

def insert_tajima_data(file_path, chromosome, tajima_column):
    with open(file_path, 'r') as file:
        next(file)  # Skip header row
        for line in file:
            columns = line.strip().split()  # Assuming tab-separated

            if len(columns) < 4:  # Ensure there are enough columns
                continue  

            start_position = int(columns[1])  # POS column
            tajima_d_value = columns[3]  # Tajima’s D column

            # Convert "nan" values to NULL in SQLite
            if tajima_d_value.lower() == "nan":
                tajima_d_value = None  # SQLite NULL
            else:
                tajima_d_value = float(tajima_d_value)  # Convert valid numbers to float

            # Debugging print statement
            print(f"Inserting: chromosome={chromosome}, start_position={start_position}, {tajima_column}={tajima_d_value}")

            # Use UPSERT to prevent duplicates
            cursor.execute(
                f"""INSERT INTO tajima_d (chromosome, start_position, {tajima_column})
                VALUES (?, ?, ?)
                ON CONFLICT(chromosome, start_position)
                DO UPDATE SET {tajima_column} = excluded.{tajima_column};""",
                (chromosome, start_position, tajima_d_value),
            )


# Process each .fst file
for file in fst_files:
    parts = file.split("_")

    try:
        population = parts[0]  # Extract population (e.g., "PJL")
        chromosome = int(parts[1].replace("chr", "").split('.')[0])  # Extract chromosome number
    except (ValueError, IndexError):
        print(f"Skipping {file} - Could not extract chromosome number or population.")
        continue

    # Ensure population is valid
    if population in fst_column_mapping:
        population_comparison = fst_column_mapping[population]  # Use mapped column name
        file_path = os.path.join(data_folder, file)
        print(f"Processing {file} → Column: {population_comparison}, Chromosome: {chromosome}")
        insert_fst_data(file_path, chromosome, population_comparison)
    else:
        print(f"Skipping {file} - No matching column for population {population}")

# Process each .Tajima.D file and insert into the correct tajima_d column
for file in tajima_files:
    parts = file.split("_")

    try:
        population = parts[0]  # Extract population (e.g., "PJL")
        chromosome = int(parts[1].replace("chr", "").split('.')[0])  # Extract chromosome number
    except (ValueError, IndexError):
        print(f"Skipping {file} - Could not extract chromosome number or population.")
        continue

    # Ensure population is valid
    if population in tajima_column_mapping:
        tajima_column = tajima_column_mapping[population]  # Use mapped column name
        file_path = os.path.join(data_folder, file)
        print(f"Processing {file} → Column: {tajima_column}, Chromosome: {chromosome}")
        insert_tajima_data(file_path, chromosome, tajima_column)
    else:
        print(f"Skipping {file} - No matching column for population {population}")

# Commit changes before retrieving sorted data
conn.commit()

# Query to retrieve sorted data
query = """
SELECT chromosome, start_position, tajima_d_BEB, tajima_d_ITU, tajima_d_GIH, tajima_d_PJL 
FROM tajima_d 
ORDER BY chromosome ASC, start_position ASC;
"""

# Execute the sorting query
cursor.execute(query)
sorted_rows = cursor.fetchall()

# Ensure sorting inside Python (failsafe)
sorted_rows = sorted(sorted_rows, key=lambda x: (x[0], x[1]))  # Sort by chromosome & start_position

# Print sorted Tajima’s D data
print("\n Sorted Tajima's D Data (Chromosome & Start Position):")
for row in sorted_rows:
    print(row)

# Close the database connection
conn.close()

print("\n Database updated successfully with sorted Tajima's D values!")

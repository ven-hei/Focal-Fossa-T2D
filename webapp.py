from flask import Flask, render_template, url_for, redirect, request
import sqlite3

app = Flask(__name__)

# Connect to available database
def get_db_connection():
    conn = sqlite3.connect('Database/web_database.db')
    conn.row_factory = sqlite3.Row  
    return conn

@app.route("/")
def home():
    return render_template('home.html')

# create new route for search result to show result on new page
@app.route("/search-result")
def result():
    query = request.args.get('query', '').strip()  # Lấy từ khóa tìm kiếm
    results = []
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT STRONGEST_SNP_RISK_ALLELE,P_VALUE, CHR_ID, CHR_POS, MAPPED_GENE FROM association 
            WHERE STRONGEST_SNP_RISK_ALLELE LIKE ? OR REGION LIKE ? OR MAPPED_GENE LIKE ?
            ORDER BY STRONGEST_SNP_RISK_ALLELE
        """, ('%' + query + '%', '%' + query + '%', '%' + query + '%'))
        results = cursor.fetchall()
        conn.close()

    return render_template('search-result.html', results=results, query=query)
    
# create route for gene function page
@app.route('/gene/<string:gene_name>')
def gene_detail(gene_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lấy thông tin người dùng
    cursor.execute("""
            SELECT * FROM association 
            WHERE MAPPED_GENE = ?
        """, (gene_name,))
    gene = cursor.fetchone()

    
    conn.close()

    if not gene:
        return "No gene information", 404

    return render_template('gene_detail.html', gene=gene)




@app.route("/about")
def about():
    return render_template('about.html')
app.run(host="0.0.0.0", port=81) 
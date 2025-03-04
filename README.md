# T2D SNP Portal

## Overview
T2D SNP Portal is  a web application that can retrieve information on single
nucleotide polymorphisms (SNPs) associated with T2D and integrate them with population
genomic (specifically in South Asian population ) and functional data. 

## Features
- **1**: 
- **2**: 
- **3**: 
- **4**: 
- **5**:

## Prerequisites
To successfully run this web application, you must have:

1. A version of Python 3.

2. On Windows, make sure the location of your Python interpreter is included in your PATH environment variable. You can check the location by running path at the command prompt. If the Python interpreter's folder isn't included, open Windows Settings, search for "environment", select Edit environment variables for your account, then edit the Path variable to include that folder.

## Installation
To install and run the application locally, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/ven-hei/Focal-Fossa-T2D.git
    ```
2. Navigate to the project directory:
    ```bash
    cd Focal-Fossa-T2D
    ```
3. Create a virtual environment:
    ```bash
    python -m venv venv
    ```
4. Activate your python virtual environment:
    - **On Windows:**
    ```bash
    venv\Scripts\activate
    ```
    - **On macOS and Linux:**
    ```bash
    source venv/bin/activate
    ```
5. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
6. Download database and vcf files from [here](https://drive.google.com/). Extract and put the Database folder in the same directory of the web application. Your directory will look like that:
    ```
    Focal-Fossa
    ├── Database
    │   ├── calculate_stats.py
    │   ├── t2d.db
    │   └── vcf_file
    ├── image.png
    ├── README.md
    ├── requirements.txt
    ├── static
    │   ├── download
    │   ├── images
    │   ├── main.css
    │   ├── plots
    │   └── stats.css
    ├── templates
    │   ├── about.html
    │   ├── base.html
    │   ├── documentation.html
    │   ├── gene_detail.html
    │   ├── home.html
    │   ├── search-result.html
    │   ├── summary_statistics.html
    │   └── summary-stats-result.html
    ├── test.py
    ├── venv
    └── webapp.py
    ```
7. Start the application:
    ```bash
    python webapp.py
    ```

## Usage
1. Open your web browser and go to `http://localhost:5000`.
2. For more information and application instruction, please read attached documentation.

## Contributing
We welcome contributions from the community. To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch:
    ```bash
    git checkout -b feature-branch
    ```
3. Make your changes and commit them:
    ```bash
    git commit -m "Description of your changes"
    ```
4. Push to the branch:
    ```bash
    git push origin feature-branch
    ```
5. Create a pull request on GitHub.


## Contact
For any questions or feedback, please contact us at [bt24807@qmul.ac.uk](mailto:bt24807@qmul.ac.uk).

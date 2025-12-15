# Project Sterling: Lab Ingestion Test Kit

## Contents
This directory contains the "Sterling Estate" dummy data and the ingestion script for the Lab Test.

### Data Files
1.  **Last_Will_2020.txt**: The official will disinheriting the son.
2.  **Assets_Estimate.csv**: List of assets and significant debts.
3.  **Secret_Email.eml**: A hidden email reversing the will's intent.
4.  **Groundskeeper_Log.md**: Contains the clue to the "Blue Envelope".

### Scripts
- **ingest_sterling.py**: The Python script to ingest these files into a local Chroma vector database and perform a test query ("Where is the blue envelope?").

## Usage Instructions (Mac)
Run these commands in this directory:

1.  **Create Virtual Environment** (Optional but recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install langchain-chroma langchain-ollama langchain-community unstructured
    ```

3.  **Run Ingestion**:
    ```bash
    python3 ingest_sterling.py
    ```

## Expected Result
The script will output the top retrieved answer, which should point to the location of the hidden Blue Envelope based on the Groundskeeper's Log.

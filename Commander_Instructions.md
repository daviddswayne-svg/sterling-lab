# Commander Instructions (Phase 3)

Run these commands from your **Windows PowerShell** terminal.

## 1. Transfer Data to Muscle (Mac)
We will create a directory on the Mac and copy the files over.
*Note: Using your verified connection `daviddswayne@10.10.10.1`.*

```powershell
# Create remote directory
ssh daviddswayne@10.10.10.1 "mkdir -p ~/sterling_lab"

# SCP files (Recursively copy the current folder content to Mac)
scp C:\Users\daves\.gemini\project_sterling\* daviddswayne@10.10.10.1:~/sterling_lab/
```

## 2. Connect & Configure
SSH into the Mac to set up the environment.

```powershell
ssh daviddswayne@10.10.10.1
```

*(Once inside the Mac terminal)*:

```bash
# Navigate to folder
cd ~/sterling_lab

# Create Virtual Environment (Recommended practice)
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install langchain-chroma langchain-ollama langchain-community unstructured
```

## 3. Execute Ingestion
Run the script to process the data and reveal the answer.

```bash
# Run the script
python3 ingest_sterling.py
```

## Expected Output
You should see:
1.  Loading of 4 documents.
2.  Splitting into chunks.
3.  Vector store creation in `./chroma_db`.
4.  Answer to "Where is the blue envelope?" pointing to the **Wine Cellar Row 4**.

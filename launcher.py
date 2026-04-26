import multiprocessing
import os
import sys
import uvicorn
from streamlit.web import cli as stcli

def run_backend():
    # Points to your backend/main.py -> app
    # Note: --reload is typically removed for production/EXE
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")

def run_frontend():
    # Programmatically calls "streamlit run frontend/app.py"
    sys.argv = [
        "streamlit", 
        "run", 
        os.path.join(os.getcwd(), "frontend", "app.py"),
        "--global.developmentMode=false",
    ]
    stcli.main()

if __name__ == "__main__":
    # Required for PyInstaller + Multiprocessing
    multiprocessing.freeze_support()
    
    p1 = multiprocessing.Process(target=run_backend)
    p2 = multiprocessing.Process(target=run_frontend)
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()

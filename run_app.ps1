# 1. Start Backend hidden (usually on port 8000)
Start-Process python -ArgumentList "-m uvicorn backend.main:app --reload" -WindowStyle Hidden

# 2. Start Frontend hidden (usually on port 8501)
Start-Process python -ArgumentList "-m streamlit run frontend/app.py" -WindowStyle Hidden

# 3. Wait a few seconds for the servers to warm up
Start-Sleep -Seconds 2

# 4. Force open the browser to your localhost link
Start-Process "http://localhost:8501" 

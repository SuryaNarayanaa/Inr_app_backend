## Get started

1. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

2. Start the backend

   ```bash
    uvicorn app.main:app --reload
   ```
   or

   ```bash
   python app/api.py
   ```

## Getting started with virtual environment

1. Create a virtual envirnoment
    ```bash
    python -m venv <envirnoment name>
    ```
2. Source the envirnoment
    ```bash
    <envirnoment name>/Scripts/activate
    ```
    For linux and macOS
    ```bash
    source <envirnoment name>/bin/activate
    ```
3. Start The backend
    ```bash
    uvicorn app.main:app --reload
   ```
#!/usr/bin/env bash
set -e

# ------------------------------------------------------------------------------
# 1. Create a fresh Python virtual environment (named "nsql_env")
# ------------------------------------------------------------------------------
echo "Creating Python virtual environment..."
python3 -m venv nsql_env

# Activate the environment
source nsql_env/bin/activate

# ------------------------------------------------------------------------------
# 2. Install dependencies
# ------------------------------------------------------------------------------
echo "Installing required Python packages..."
pip install --upgrade pip
# Streamlit for the web app
# Requests to call Ollama
# DuckDB for local SQL execution
pip install streamlit requests duckdb

# ------------------------------------------------------------------------------
# 3. Create the Streamlit app script (duckdb_nsql_app.py)
# ------------------------------------------------------------------------------
cat << 'EOF' > duckdb_nsql_app.py
import streamlit as st
import requests
import duckdb
import re

# ------------------------------------------------------------------------------
# CONFIG & INITIALIZATION
# ------------------------------------------------------------------------------
st.set_page_config(page_title="DuckDB + Ollama Demo", layout="wide")

# We can create or connect to a local DuckDB database file, e.g. "mydata.db".
# For demo purposes, we create an in-memory database:
conn = duckdb.connect(database=':memory:')
# (Optionally, load or create some sample tables here.)
# Example: creating a test table
conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INT, username VARCHAR, created_at TIMESTAMP)")
# Insert some sample data
conn.execute("INSERT INTO users VALUES (1, 'alice', '2024-01-01 10:00:00')")
conn.execute("INSERT INTO users VALUES (2, 'bob',   '2024-01-02 09:30:00')")

# Ollama server endpoint
OLLAMA_URL = "http://localhost:11400/generate"

# Example system prompt or instructions for the LLM on how to generate SQL
SYSTEM_PROMPT = """
SYSTEM: You are a helpful assistant that translates natural language questions into valid SQL.
USER: {user_question}

ASSISTANT: 
"""

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def query_ollama(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama server (running on port 11400).
    Returns the raw LLM output (string).
    """
    try:
        response = requests.post(OLLAMA_URL, json={"prompt": prompt})
        response.raise_for_status()
        return response.json().get("content", "")
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with Ollama: {e}")
        return ""

def extract_sql(llm_output: str) -> str:
    """
    Attempt to extract an SQL statement from the LLM output.
    This function uses a simple regex or marker-based approach.
    Adjust as needed based on your LLM's format.
    """
    # If the LLM encloses SQL in triple backticks or something similar, you can parse it out.
    # For example, look for ```sql ... ```
    pattern = r"```sql(.*?)```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: if no code block found, just return everything
    return llm_output.strip()

def run_sql_in_duckdb(sql_query: str):
    """
    Execute SQL on DuckDB and return results as a list of tuples + column names.
    """
    try:
        result = conn.execute(sql_query).fetchall()
        col_names = [desc[0] for desc in conn.description]
        return col_names, result
    except Exception as e:
        st.error(f"SQL error: {e}")
        return [], []

# ------------------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------------------
st.title("DuckDB + Ollama Natural SQL Demo")

st.markdown("""
Enter a **natural language** question. We'll:
1. Send it to Ollama to generate SQL.
2. Parse the SQL and run it in DuckDB.
3. Show you the results here.
""")

with st.expander("Sample Data"):
    st.write("We created a small `users` table in DuckDB with sample rows:")
    sample_rows = conn.execute("SELECT * FROM users").fetchdf()
    st.dataframe(sample_rows)

user_question = st.text_area("Ask your question about this data:", value="Show me the day with the most users joining")

if st.button("Generate & Run SQL"):
    # Step 1: Build prompt and call Ollama
    prompt_text = SYSTEM_PROMPT.format(user_question=user_question)
    st.info(f"**Sending prompt to Ollama**:\n{prompt_text}")
    llm_output = query_ollama(prompt_text)

    st.markdown("#### LLM Raw Output:")
    st.code(llm_output, language="sql")

    # Step 2: Extract SQL from the LLM output
    sql_query = extract_sql(llm_output)
    st.markdown("#### Extracted SQL Query:")
    st.code(sql_query, language="sql")

    # Step 3: Run in DuckDB
    col_names, results = run_sql_in_duckdb(sql_query)

    if results:
        st.markdown("#### Query Results:")
        st.dataframe(results, columns=col_names)
EOF

# ------------------------------------------------------------------------------
# 4. Launch the Streamlit app
# ------------------------------------------------------------------------------
echo "Launching Streamlit app..."
streamlit run duckdb_nsql_app.py
EOF

echo "Done! Streamlit is running above. If it doesn't launch automatically,"
echo "open the printed URL (usually http://localhost:8501) in your browser."

import streamlit as st
import requests
import duckdb
import re

# ------------------------------------------------------------------------------
# CONFIG & INITIALIZATION
# ------------------------------------------------------------------------------
st.set_page_config(page_title="DuckDB + Ollama Demo", layout="wide")

# We connect to an in-memory DuckDB (':memory:').
# For real data, replace with e.g. duckdb.connect("mydatabase.db")
conn = duckdb.connect(database=':memory:')

# Create a sample table called "users" just for demonstration:
conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INT, username VARCHAR, created_at TIMESTAMP)")

# For illustration, let's insert some sample rows (only if empty):
row_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
if row_count == 0:
    conn.execute("INSERT INTO users VALUES (1, 'alice', '2024-01-01 10:00:00')")
    conn.execute("INSERT INTO users VALUES (2, 'bob',   '2024-01-02 09:30:00')")
    conn.execute("INSERT INTO users VALUES (3, 'charlie', '2024-01-02 15:45:00')")

# Ollama server endpoint (make sure you're running `ollama serve --model <model> --port 11400`)
OLLAMA_URL = "http://localhost:11400/generate"

# Example system instructions for the LLM
SYSTEM_PROMPT = """
SYSTEM: You are a helpful assistant that translates natural language questions into valid SQL.
Use the table(s) and columns you know exist. Return only the SQL query. 
If you include code blocks, please enclose them in triple backticks like ```sql ... ```.

USER: {user_question}
ASSISTANT:
"""

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def query_ollama(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama server (running on port 11400).
    Returns the raw LLM output as a string.
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
    If the LLM encloses it in ```sql ... ```, parse it out with a simple regex.
    """
    pattern = r"```sql(.*?)```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: if no code block found, return the entire output
    return llm_output.strip()

def run_sql_in_duckdb(sql_query: str):
    """
    Execute SQL on DuckDB and return results as (column_names, rows).
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
2. Show you the generated SQL in a table.
3. Ask if you want to run it in DuckDB.
4. Display the results below.
""")

# Show sample data for reference
with st.expander("Sample Data in DuckDB"):
    st.write("We have a simple `users` table with:")
    sample_rows = conn.execute("SELECT * FROM users").fetchdf()
    st.dataframe(sample_rows)

# Text area for user question
user_question = st.text_area(
    "Ask your question about this data:", 
    value="Show me the day with the most users joining"
)

if st.button("Generate SQL"):
    # Build prompt
    prompt_text = SYSTEM_PROMPT.format(user_question=user_question)
    
    st.info(f"**Prompt sent to Ollama**:\n{prompt_text}")
    
    # Call Ollama LLM
    llm_output = query_ollama(prompt_text)
    
    # Display raw LLM response
    st.markdown("### Raw LLM Output:")
    st.code(llm_output, language="sql")
    
    # Extract SQL
    sql_query = extract_sql(llm_output)
    
    st.markdown("### Extracted SQL Query:")
    # Show the SQL in a single-row table for clarity
    st.table([[sql_query]])
    
    # Provide a button to confirm running the query
    if st.button("Run this query in DuckDB"):
        col_names, results = run_sql_in_duckdb(sql_query)
        if results:
            st.markdown("#### Query Results:")
            st.dataframe(results, columns=col_names)
        else:
            st.warning("No results or the query didn't return anything.")

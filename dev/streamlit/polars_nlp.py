import streamlit as st
import requests
import polars as pl
import re

# ------------------------------------------------------------------------------
# CONFIG & INITIALIZATION
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Polars + Ollama Natural Language Demo", layout="wide")

# Create a sample Polars DataFrame ("users" table)
df = pl.DataFrame({
    "user_id": [1, 2, 3],
    "username": ["alice", "bob", "charlie"],
    "created_at": ["2024-01-01 10:00:00", "2024-01-02 09:30:00", "2024-01-02 15:45:00"]
})

# Ollama server endpoint (ensure you have ollama running locally, e.g.:
# `ollama serve --model /path/to/model.bin --port 11400`)
OLLAMA_URL = "http://localhost:11400/generate"

# Example system instructions for the LLM
SYSTEM_PROMPT = """
SYSTEM: You are a helpful assistant that translates natural language questions into valid SQL.
Return only the SQL query in triple backticks like ```sql ... ```.

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
    If the LLM encloses it in ```sql ... ```, parse it out with a regex.
    """
    pattern = r"```sql(.*?)```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return llm_output.strip()

# A very naive function to handle certain SQL queries in Polars.
# For real applications, you'd need a robust SQL parser or custom mapping logic.
def run_sql_in_polars(sql_query: str, data: pl.DataFrame) -> pl.DataFrame:
    """
    Demonstrates how to manually interpret a specific SQL pattern in Polars.
    E.g.: 
    SELECT created_at::DATE as day, COUNT(*) as user_count
    FROM users
    GROUP BY day
    ORDER BY user_count DESC
    LIMIT 1;
    """
    # Lowercase for naive matching
    lower_sql = sql_query.lower()

    # Example: If the question is about grouping by day and counting
    # (like "show me the day with the most users joining"):
    if "group by" in lower_sql and "created_at" in lower_sql and "count(" in lower_sql:
        # We'll parse out "day" by casting created_at to a date and counting.
        # Pseudocode for the typical logic:
        polars_df = (
            data
            .with_column(
                pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S").alias("created_dt")
            )
            .with_column(pl.col("created_dt").dt.truncate("1d").alias("day"))  # or dt.date()
            .groupby("day")
            .agg([
                pl.count().alias("user_count")
            ])
            .sort("user_count", descending=True)
        )
        # If there's a LIMIT 1 in the SQL, we'll just head(1)
        if "limit 1" in lower_sql:
            polars_df = polars_df.head(1)

        return polars_df

    # If we don't have a known pattern, just return the original data
    # or an empty DataFrame with a message
    return pl.DataFrame()

# ------------------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------------------
st.title("Polars + Ollama Natural Language Demo")

st.markdown("""
Enter a **natural language** question. We'll:
1. Send it to Ollama to generate SQL.
2. Show the SQL to you.
3. If you approve, we'll attempt to interpret the SQL in Polars 
   (using a naive pattern match).
""")

# Show sample data
with st.expander("Sample DataFrame"):
    st.write("We have a `users` table (Polars DataFrame):")
    st.dataframe(df)

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

    # Show the extracted SQL in a single-row table
    st.markdown("### Extracted SQL Query:")
    st.table([[sql_query]])

    # Provide a button to confirm running the query logic in Polars
    if st.button("Run this query in Polars"):
        result_df = run_sql_in_polars(sql_query, df)
        if result_df.is_empty():
            st.warning("We don't have a custom parser for that SQL pattern yet!")
        else:
            st.markdown("#### Polars Output:")
            st.dataframe(result_df)

import streamlit as st
import polars as pl
import re
import ollama

# Create a sample Polars DataFrame (pretend it's "taxi" table)
df = pl.DataFrame({
    "VendorID": [1, 2, 2],
    "tpep_pickup_datetime": [
        "2024-01-01 00:15:27",
        "2024-01-01 01:45:30",
        "2024-01-01 02:10:10",
    ],
    "tpep_dropoff_datetime": [
        "2024-01-01 00:25:00",
        "2024-01-01 02:00:00",
        "2024-01-01 02:25:00",
    ],
    "passenger_count": [1.0, 2.0, 1.0],
    "trip_distance": [1.2, 3.5, 2.2],
    "fare_amount": [7.0, 13.5, 10.0],
    "extra": [0.5, 1.0, 0.5],
    "tip_amount": [1.0, 2.0, 1.5],
    "tolls_amount": [0.0, 0.0, 1.0],
    "improvement_surcharge": [0.3, 0.3, 0.3],
    "total_amount": [8.8, 16.8, 13.3],
})

# A simple system prompt describing the schema
SYSTEM_SCHEMA = """Here is the database schema that the SQL query will run on:
CREATE TABLE taxi (
    VendorID bigint,
    tpep_pickup_datetime timestamp,
    tpep_dropoff_datetime timestamp,
    passenger_count double,
    trip_distance double,
    fare_amount double,
    extra double,
    tip_amount double,
    tolls_amount double,
    improvement_surcharge double,
    total_amount double
);
"""

def query_ollama(user_prompt: str) -> str:
    """
    Generate SQL via Ollama, using duckdb-nsql:7b-q4_0.
    """
    response_dict = ollama.generate(
        model="duckdb-nsql:7b-q4_0",
        system=SYSTEM_SCHEMA,
        prompt=user_prompt,
    )
    return response_dict.get("response", "")

def extract_sql(llm_output: str) -> str:
    """
    If the LLM encloses SQL in ```sql ... ```, parse it out.
    Otherwise, return the raw string.
    """
    pattern = r"```sql(.*?)```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return llm_output.strip()

st.title("Minimal Polars + Ollama SQL Demo")

# Display the sample DataFrame for reference
with st.expander("Sample 'taxi' DataFrame"):
    st.dataframe(df)

# Let the user type a question
user_prompt = st.text_input("Ask a question (the model will return SQL):", "SELECT * FROM taxi")

if st.button("Generate & Run SQL"):
    # Step 1: Generate SQL from Ollama
    llm_output = query_ollama(user_prompt)
    st.write("### LLM Output")
    st.code(llm_output, language="sql")

    # Step 2: Extract actual SQL (handle possible code fences)
    sql_query = extract_sql(llm_output)
    st.write("### Using SQL:")
    st.code(sql_query, language="sql")

    # Step 3: Execute on Polars df
    try:
        results = df.sql(query=sql_query, table_name="taxi")
        st.write("### Query Results")
        st.dataframe(results)
    except Exception as e:
        st.error(f"SQL Error: {e}")

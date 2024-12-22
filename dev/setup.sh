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
pip install "transformers==4.35.2" torch safetensors accelerate

# ------------------------------------------------------------------------------
# 3. Create the Python script that loads and runs the model
# ------------------------------------------------------------------------------
cat << 'EOF' > run_nsql.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    model_name = "chatdb/natural-sql-7b"
    print(f"Loading tokenizer for {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    print(f"Loading model {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    # Sample prompt from the model card
    prompt = """# Task
Generate a SQL query to answer the following question: "Show me the day with the most users joining"

### PostgreSQL Database Schema
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

# SQL
Here is the SQL query that answers the question: "Show me the day with the most users joining"
'''sql
"""

    print("Generating SQL from prompt...")
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    generated_ids = model.generate(
        **inputs,
        num_return_sequences=1,
        max_new_tokens=200,
        eos_token_id=100001,
        pad_token_id=100001,
        do_sample=False,
        num_beams=1,
    )

    output = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    # Extract everything after the ```sql block
    sql_response = output.split("```sql")[-1].strip()
    print("\n--- Generated SQL ---")
    print(sql_response)

if __name__ == "__main__":
    main()
EOF

# ------------------------------------------------------------------------------
# 4. Run the Python script
# ------------------------------------------------------------------------------
echo "Running the model script..."
python run_nsql.py

echo "Done!"

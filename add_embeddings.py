# add_embeddings.py
import json
import openai
from openai import OpenAI
import time
from tqdm import tqdm
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set your OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text, model="text-embedding-3-small"):
    """Get embedding for a text using OpenAI API."""
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def add_embeddings_to_jsonl(input_file, output_file):
    """Add embeddings to each chunk in JSONL file."""
    chunks = []
    
    # Read input file
    print("Loading chunks...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"Processing {len(chunks)} chunks...")
    
    # Add embeddings with progress bar
    for i, chunk in enumerate(tqdm(chunks)):
        if 'embedding' not in chunk:  # Skip if already has embedding
            embedding = get_embedding(chunk['text'])
            if embedding:
                chunk['embedding'] = embedding
            else:
                print(f"Failed to get embedding for chunk {i}")
        
        # Rate limiting - OpenAI has limits
        if i % 100 == 0:
            time.sleep(1)
    
    # Write output file
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print("Done!")

if __name__ == "__main__":
    input_file = "theological_chunks.jsonl"
    output_file = "theological_chunks_with_embeddings.jsonl"
    
    add_embeddings_to_jsonl(input_file, output_file)
#!/usr/bin/env python3
"""
Migration script to load existing chunks into ChromaDB.

This script reads chunks from the deployed directory and loads them into ChromaDB
for faster vector similarity search. Run this once after installing ChromaDB.
"""

import json
import chromadb
from pathlib import Path
from chromadb.config import Settings

def migrate_to_chroma():
    """Migrate existing chunks to ChromaDB"""
    
    # Get paths
    script_dir = Path(__file__).parent
    deployed_dir = script_dir / 'theological_processing' / '05_deployed'
    chroma_db_path = script_dir / 'chroma_db'
    
    if not deployed_dir.exists():
        print(f"Error: Deployed directory not found: {deployed_dir}")
        return False
    
    # Initialize ChromaDB client (persistent)
    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(
        path=str(chroma_db_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create collection
    collection_name = "theological_corpus"
    try:
        collection = client.get_collection(name=collection_name)
        print(f"Found existing collection: {collection_name}")
        print(f"Current count: {collection.count()}")
        
        response = input(f"\nCollection already exists with {collection.count()} chunks. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return False
        
        # Delete existing collection
        client.delete_collection(name=collection_name)
        print("Deleted existing collection.")
    except:
        print(f"Creating new collection: {collection_name}")
    
    # Create collection with cosine distance metric
    # ChromaDB defaults to L2, but we want cosine for normalized embeddings
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Theological corpus with embeddings"},
        # Use cosine distance for normalized embeddings
        # This makes distance = 1 - cosine_similarity
    )
    
    # Load chunks from JSONL files
    jsonl_files = [f for f in deployed_dir.glob('*.jsonl') if 'backup' not in f.name.lower()]
    
    if not jsonl_files:
        print(f"Warning: No JSONL files found in {deployed_dir}")
        return False
    
    print(f"\nFound {len(jsonl_files)} JSONL files to process...")
    
    # Prepare data for ChromaDB
    ids = []
    embeddings = []
    documents = []
    metadatas = []
    
    chunk_count = 0
    skipped_count = 0
    
    for jsonl_file in jsonl_files:
        print(f"Processing {jsonl_file.name}...")
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        chunk = json.loads(line.strip())
                        
                        # Validate chunk has required fields
                        if not chunk.get('text') or not chunk.get('embedding'):
                            skipped_count += 1
                            continue
                        
                        chunk_id = chunk.get('id', f'chunk_{chunk_count}')
                        
                        # Prepare metadata (ChromaDB requires string values)
                        metadata = {
                            'source': str(chunk.get('source', 'Unknown')),
                            'author': str(chunk.get('author', 'Unknown')),
                            'chunk_index': str(chunk.get('chunk_index', chunk_count)),
                        }
                        
                        # Add structure_path if available
                        if chunk.get('metadata', {}).get('structure_path'):
                            metadata['structure_path'] = str(chunk['metadata']['structure_path'])
                        
                        # Store full metadata as JSON string for later retrieval
                        metadata['full_metadata'] = json.dumps(chunk.get('metadata', {}))
                        
                        ids.append(chunk_id)
                        embeddings.append(chunk['embedding'])
                        documents.append(chunk['text'])
                        metadatas.append(metadata)
                        
                        chunk_count += 1
                        
                        # Batch insert every 1000 chunks
                        if chunk_count % 1000 == 0:
                            print(f"  Processed {chunk_count} chunks...")
                            collection.add(
                                ids=ids,
                                embeddings=embeddings,
                                documents=documents,
                                metadatas=metadatas
                            )
                            # Clear batches
                            ids = []
                            embeddings = []
                            documents = []
                            metadatas = []
                            
                    except json.JSONDecodeError:
                        skipped_count += 1
                        continue
    
    # Insert remaining chunks
    if ids:
        print(f"  Inserting final {len(ids)} chunks...")
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    print(f"\n✅ Migration complete!")
    print(f"   Total chunks migrated: {chunk_count}")
    print(f"   Skipped chunks: {skipped_count}")
    print(f"   ChromaDB collection: {collection_name}")
    print(f"   Database path: {chroma_db_path}")
    print(f"   Final collection count: {collection.count()}")
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("ChromaDB Migration Script")
    print("=" * 60)
    print()
    
    success = migrate_to_chroma()
    
    if success:
        print("\n✅ Migration successful! You can now use ChromaDB for vector search.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")


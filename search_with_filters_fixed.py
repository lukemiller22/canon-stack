def search_with_filters(query, query_embedding, analysis, selected_sources=None):
    """Perform intelligent two-stage search: ChromaDB top 100 → re-rank with metadata → top 15"""
    try:
        if not query_embedding:
            return []
        
        start_time = time.time()
        
        # STAGE 1: ChromaDB vector search - get top 100 by similarity
        if chroma_collection:
            # Use ChromaDB for fast vector search
            stage1_start = time.time()
            
            # Build where clause for source filtering if needed
            where_clause = None
            if selected_sources and len(selected_sources) > 0:
                # ChromaDB where clause: {"source": {"$in": [...]}}
                # Need to map source IDs back to source names
                source_names = []
                for source_info in available_sources:
                    if source_info['id'] in selected_sources:
                        source_names.append(source_info['name'])
                if source_names:
                    where_clause = {"source": {"$in": source_names}}
            
            # Query ChromaDB for top 100 results
            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=100,  # Get top 100 for re-ranking
                where=where_clause
            )
            
            stage1_time = time.time() - stage1_start
            print(f"[TIMING] Stage 1 (ChromaDB top 100): {stage1_time:.3f}s")
            
            # Map ChromaDB results back to full chunk objects
            top_100_chunks = []
            if results['ids'] and len(results['ids'][0]) > 0:
                # Create mapping from chunk ID to full chunk data
                chunk_map = {chunk.get('id'): chunk for chunk in dataset}
                
                # Get distances (ChromaDB returns distances, convert to similarities)
                distances = results['distances'][0] if results.get('distances') else []
                
                for idx, chunk_id in enumerate(results['ids'][0]):
                    if chunk_id in chunk_map:
                        chunk = chunk_map[chunk_id].copy()
                        # Convert distance to similarity (ChromaDB uses cosine distance: 1 - similarity)
                        distance = distances[idx] if idx < len(distances) else 1.0
                        similarity = 1.0 - distance  # Convert distance to similarity
                        chunk['similarity_score'] = float(similarity)
                        top_100_chunks.append(chunk)
        else:
            # Fallback: use old method if ChromaDB not available
            print("[WARNING] ChromaDB not available, using slower fallback method")
            stage1_start = time.time()
            
            # Filter dataset by selected sources
            filtered_dataset = dataset
            if selected_sources and len(selected_sources) > 0:
                filtered_dataset = []
                for chunk in dataset:
                    source_key = f"{chunk.get('source', 'Unknown')}_{chunk.get('author', 'Unknown')}"
                    source_id = source_key.lower().replace(' ', '_').replace('.', '').replace('/', '_')
                    if source_id in selected_sources:
                        filtered_dataset.append(chunk)
            
            if not filtered_dataset:
                return []
            
            # Calculate similarities
            query_embedding_array = np.array([query_embedding])
            chunk_embeddings = []
            valid_chunks = []
            
            for chunk in filtered_dataset:
                if 'embedding' in chunk and chunk['embedding']:
                    chunk_embeddings.append(chunk['embedding'])
                    valid_chunks.append(chunk)
            
            if not chunk_embeddings:
                return []
            
            embeddings_array = np.array(chunk_embeddings)
            similarities = cosine_similarity(query_embedding_array, embeddings_array)[0]
            
            # Get top 100 by similarity
            scored_pairs = [(valid_chunks[i], similarities[i]) for i in range(len(valid_chunks))]
            scored_pairs.sort(key=lambda x: x[1], reverse=True)
            top_100_chunks = [chunk.copy() for chunk, score in scored_pairs[:100]]
            for i, chunk in enumerate(top_100_chunks):
                chunk['similarity_score'] = float(scored_pairs[i][1])
            
            stage1_time = time.time() - stage1_start
            print(f"[TIMING] Stage 1 (Fallback top 100): {stage1_time:.3f}s")
        
        if not top_100_chunks:
            return []
        
        # STAGE 2: Re-rank top 100 with metadata boost
        stage2_start = time.time()
        scored_chunks = []
        for chunk in top_100_chunks:
            base_score = chunk.get('similarity_score', 0.0)
            metadata_boost = calculate_metadata_boost(chunk, analysis)
            final_score = base_score + metadata_boost
            
            scored_chunks.append({
                **chunk,
                'similarity_score': float(base_score),
                'metadata_boost': float(metadata_boost),
                'final_score': float(final_score)
            })
        
        # Sort by final score and return top 15
        scored_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        top_15 = scored_chunks[:15]
        
        stage2_time = time.time() - stage2_start
        total_time = time.time() - start_time
        print(f"[TIMING] Stage 2 (Re-rank top 100): {stage2_time:.3f}s")
        print(f"[TIMING] Total search time: {total_time:.3f}s")
        
        return top_15
        
    except Exception as e:
        print(f"Error in search: {e}")
        import traceback
        traceback.print_exc()
        return []

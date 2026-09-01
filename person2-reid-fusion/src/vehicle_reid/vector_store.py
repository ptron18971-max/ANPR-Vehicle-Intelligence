import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Tuple

class FaissVectorStore:
    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        # IndexFlatIP performs inner product search. With L2-normalized vectors, 
        # inner product is mathematically equivalent to cosine similarity.
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata_store: Dict[int, Dict[str, Any]] = {}

    def add(self, embedding: np.ndarray, metadata: Dict[str, Any]) -> int:
        """
        Adds a single L2-normalized vehicle embedding and its associated metadata to the store.
        """
        if embedding.ndim == 1:
            embedding = np.expand_dims(embedding, axis=0)
        
        if embedding.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {embedding.shape[1]}")

        # Ensure vector is float32 and contiguous for FAISS
        vector = np.ascontiguousarray(embedding, dtype=np.float32)
        
        vector_id = self.index.ntotal
        self.index.add(vector)
        self.metadata_store[vector_id] = metadata
        
        return vector_id

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the FAISS index for the top-k most similar vehicle embeddings 
        and attaches their corresponding metadata.
        """
        if self.index.ntotal == 0:
            return []

        if query_embedding.ndim == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)

        query = np.ascontiguousarray(query_embedding, dtype=np.float32)
        actual_k = min(top_k, self.index.ntotal)
        
        distances, indices = self.index.search(query, actual_k)
        
        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            metadata = self.metadata_store.get(idx, {})
            results.append({
                "vector_id": int(idx),
                "similarity_score": float(score),
                "metadata": metadata
            })
            
        return results

    def save(self, index_path: str, metadata_path: str) -> None:
        """Saves the FAISS index and companion metadata store to disk."""
        faiss.write_index(self.index, index_path)
        with open(metadata_path, "wb") as f:
            pickle.dump(self.metadata_store, f)

    def load(self, index_path: str, metadata_path: str) -> None:
        """Loads a persisted FAISS index and companion metadata store from disk."""
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        if os.path.exists(metadata_path):
            with open(metadata_path, "rb") as f:
                self.metadata_store = pickle.load(f)
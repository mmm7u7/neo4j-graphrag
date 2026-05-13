#!/usr/bin/env python3
"""
Rebuild vector index for GraphRAG system.
Run this after generating/updating node descriptions.

Usage:
    python scripts/rebuild-vector-index.py
"""

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import sys
import os

# Default config - override via environment or edit
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "YOUR_PASSWORD")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", ".")


def rebuild_index():
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    print("Fetching nodes with descriptions...")
    with driver.session() as session:
        nodes = session.run("""
            MATCH (n)
            WHERE n.name IS NOT NULL
            RETURN id(n) as id, labels(n)[0] as type, n.name as name, n.description as description
        """).data()
    
    print(f"Found {len(nodes)} nodes")
    
    print("Building texts with descriptions...")
    texts = []
    for n in nodes:
        text = f"{n['type']}: {n['name']}"
        if n.get('description'):
            # Truncate long descriptions to avoid embedding noise
            desc = n['description'][:150] if len(n.get('description', '')) > 150 else n['description']
            text += f"。{desc}"
        texts.append(text)
    
    print("Generating embeddings (this may take a few minutes)...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Save to files
    embeddings_path = os.path.join(OUTPUT_DIR, "embeddings.npy")
    nodes_path = os.path.join(OUTPUT_DIR, "nodes.json")
    
    print(f"Saving embeddings to {embeddings_path}...")
    np.save(embeddings_path, embeddings)
    
    print(f"Saving node info to {nodes_path}...")
    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False)
    
    driver.close()
    
    print(f"\nDone! Vector index rebuilt:")
    print(f"  - Nodes: {len(nodes)}")
    print(f"  - Embedding shape: {embeddings.shape}")
    print(f"  - Files: {embeddings_path}, {nodes_path}")


if __name__ == "__main__":
    rebuild_index()

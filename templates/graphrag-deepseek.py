#!/usr/bin/env python3
"""
Neo4j GraphRAG Implementation Template
Uses DeepSeek API (OpenAI-compatible) as LLM backend

Usage:
    1. Copy this template and customize configuration
    2. Run: python graphrag_system.py
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np

# ============ CONFIGURATION ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"

# DeepSeek API (OpenAI-compatible)
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # or "deepseek-reasoner"

# ============ NEO4J CONNECTION ============
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def query(self, cypher, parameters=None):
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]
    
    def get_schema(self):
        """Get graph schema (labels, relationships, properties)"""
        labels = self.query("CALL db.labels() YIELD label RETURN collect(label) as labels")[0]['labels']
        rel_types = self.query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types")[0]['types']
        return {"labels": labels, "relationships": rel_types}

# ============ VECTOR STORE ============
class VectorStore:
    def __init__(self, neo4j_conn: Neo4jConnection, embedding_model: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.neo4j = neo4j_conn
        self.model = SentenceTransformer(embedding_model)
        self.nodes = []
        self.embeddings = None
    
    def build_index(self, limit: int = 5000):
        """Build vector index from graph nodes"""
        cypher = f"""
        MATCH (n)
        WHERE n.name IS NOT NULL
        RETURN id(n) as id, labels(n)[0] as type, n.name as name
        LIMIT {limit}
        """
        self.nodes = self.neo4j.query(cypher)
        
        if self.nodes:
            texts = [f"{n['type']}: {n['name']}" for n in self.nodes]
            self.embeddings = self.model.encode(texts, show_progress_bar=True)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Semantic search for relevant nodes"""
        if self.embeddings is None:
            return []
        
        query_embedding = self.model.encode([query])
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [{**self.nodes[idx], 'score': float(similarities[idx])} for idx in top_indices]

# ============ LLM CLIENT ============
class LLMClient:
    """
    OpenAI-compatible LLM client.
    Works with: DeepSeek, OpenAI, Azure, local servers (vLLM, Ollama with OpenAI compat)
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content

# ============ GRAPH RAG ============
class GraphRAG:
    def __init__(self, neo4j_config: dict, llm_config: dict):
        self.neo4j = Neo4jConnection(**neo4j_config)
        self.llm = LLMClient(**llm_config)
        self.vector_store = VectorStore(self.neo4j)
        self.schema = self.neo4j.get_schema()
    
    def initialize(self):
        """Build vector index - call once at startup"""
        print("Building vector index...")
        self.vector_store.build_index()
        print(f"Indexed {len(self.vector_store.nodes)} nodes")
    
    def _generate_cypher(self, question: str, context_nodes: List[Dict]) -> str:
        """Use LLM to generate Cypher query"""
        prompt = f"""Generate a Neo4j Cypher query for this question.

Graph schema (partial):
Labels: {self.schema['labels'][:20]}
Relationships: {self.schema['relationships'][:20]}

Relevant nodes found:
{json.dumps(context_nodes[:5], ensure_ascii=False)}

Question: {question}

Output only the Cypher query, no explanation."""
        
        cypher = self.llm.generate(prompt)
        # Clean up code blocks
        cypher = re.sub(r'^```\w*\n?', '', cypher.strip())
        cypher = re.sub(r'\n?```$', '', cypher)
        return cypher
    
    def query(self, question: str) -> Dict:
        """Execute RAG query: retrieve + generate"""
        # 1. Semantic search
        context_nodes = self.vector_store.search(question)
        
        # 2. Generate and execute Cypher
        cypher = self._generate_cypher(question, context_nodes)
        graph_data = []
        try:
            graph_data = self.neo4j.query(cypher)
        except Exception as e:
            print(f"Query error: {e}")
        
        # 3. Generate answer
        answer_prompt = f"""Answer based on the retrieved graph data.

Graph data:
{json.dumps(graph_data[:10], ensure_ascii=False, indent=2)}

Context nodes:
{json.dumps(context_nodes[:5], ensure_ascii=False)}

Question: {question}

Provide a clear, accurate answer based on the data."""
        
        answer = self.llm.generate(answer_prompt)
        
        return {
            "question": question,
            "answer": answer,
            "graph_data": graph_data[:5],
            "cypher": cypher
        }
    
    def close(self):
        self.neo4j.close()

# ============ MAIN ============
if __name__ == "__main__":
    # Initialize
    rag = GraphRAG(
        neo4j_config={
            "uri": NEO4J_URI,
            "user": NEO4J_USER,
            "password": NEO4J_PASSWORD
        },
        llm_config={
            "api_key": DEEPSEEK_API_KEY,
            "base_url": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_MODEL
        }
    )
    
    rag.initialize()
    
    # Interactive loop
    print("\nGraphRAG System Ready. Type 'quit' to exit.\n")
    while True:
        q = input("Question: ").strip()
        if q.lower() in ['quit', 'exit']:
            break
        if q:
            result = rag.query(q)
            print(f"\nAnswer: {result['answer']}\n")
    
    rag.close()

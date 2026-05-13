---
name: neo4j-graphrag
description: Build Retrieval-Augmented Generation systems on Neo4j knowledge graphs.
version: 1.3.0
---

# Neo4j GraphRAG

Build Retrieval-Augmented Generation systems on Neo4j knowledge graphs.

## Triggers
- User mentions "knowledge graph RAG", "Neo4j RAG", "graph-based QA"
- User asks to query or build applications on Neo4j graph data
- Need to connect Neo4j with LLMs for question answering

## Neo4j Setup & Troubleshooting

### Starting Neo4j (Homebrew)
```bash
neo4j start
neo4j status
neo4j stop
```

### Pitfall: Lock File Conflict After Version Upgrade

**Symptoms**: `FileLockException: Lock file has been locked by another process: .../store_lock`

**Cause**: Old Neo4j process from previous version still running, holding the database lock.

**Fix**:
```bash
# 1. Kill all Neo4j processes
pkill -f "neo4j"

# 2. Remove the lock file
rm -f /opt/homebrew/var/neo4j/data/databases/store_lock

# 3. Restart Neo4j
neo4j start
```

### Verify Neo4j is Running
```bash
# Check ports
lsof -i :7474 -i :7687

# Test HTTP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:7474
# Should return 200

# Open browser
open http://localhost:7474
```

### Default Credentials
- URL: http://localhost:7474 (HTTP), bolt://localhost:7687 (Bolt)
- Default: neo4j/neo4j (must change on first login)

## GraphRAG Architecture

### Core Components
1. **Graph Database**: Neo4j stores entities and relationships
2. **Vector Store**: Embedding vectors for semantic search
3. **Retriever**: Hybrid graph + vector retrieval
4. **LLM**: Generate answers from retrieved context

### Implementation Options

#### Option 1: Neo4j GraphRAG (Official)
```bash
pip install neo4j-graphrag
```
- Native Neo4j integration
- Graph-based retrieval
- Built-in vector indexing

#### Option 2: LangChain + Neo4j
```bash
pip install langchain-neo4j
```
- LangChain ecosystem
- Chain-based workflows
- Multiple retriever types

#### Option 3: LlamaIndex + Neo4j
```bash
pip install llama-index-graph-stores-neo4j
```
- Knowledge graph index
- GraphRAG query engine
- Flexible retrieval strategies

#### Option 4: Custom Implementation (Recommended for Full Control)
See `templates/graphrag-deepseek.py` for a complete working example.

## LLM Backends (OpenAI-Compatible API)

### DeepSeek API
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com/v1"
)
# Models: "deepseek-chat", "deepseek-reasoner"
```

### Other OpenAI-Compatible Endpoints
- **OpenAI**: `base_url="https://api.openai.com/v1"`
- **Azure OpenAI**: `base_url="https://YOUR_RESOURCE.openai.azure.com"`
- **vLLM**: `base_url="http://localhost:8000/v1"`
- **Ollama**: `base_url="http://localhost:11434/v1"`

## Templates

- `templates/graphrag-deepseek.py` - Complete GraphRAG implementation with DeepSeek/any OpenAI-compatible LLM
- `templates/config.yaml` - Configuration file template with all tunable parameters

## Common Workflows

### 1. Schema Inspection
```cypher
-- List all node labels
CALL db.labels()

-- List all relationship types
CALL db.relationshipTypes()

-- Get property keys
CALL db.propertyKeys()

-- Full schema
CALL db.schema.visualization()
```

### 2. Test Connection (Python)
```python
from neo4j import GraphDatabase

driver = GraphDatabase.Driver(
    "bolt://localhost:7687",
    auth=("neo4j", "your_password")
)
driver.verify_connectivity()
```

### 3. Sample GraphRAG Query Pattern
```cypher
-- Find relevant subgraph based on entity match
MATCH path = (start:Entity)-[r*1..3]-(end:Entity)
WHERE start.name CONTAINS $query_term
RETURN path
```

## Chunk Strategies & Parameter Tuning

See `references/chunk-strategies.md` for detailed guidance on:
- GraphRAG "chunk" strategies (simple/standard/rich/graph)
- Embedding model selection for different languages
- Parameter tuning recipes for speed vs accuracy

## Knowledge Graph Quality Evaluation

Before and after building RAG, evaluate KG quality:

```bash
python scripts/kg-evaluator.py
```

See `references/kg-evaluation.md` for:
- Evaluation framework (completeness, coverage, connectivity, consistency)
- Scoring formulas and quality levels
- Manual review checklist

## Knowledge Graph Repair

Common issues and fixes:

```bash
# Run all repairs
python scripts/kg-repair.py

# Only merge duplicates  
python scripts/kg-repair.py --merge-only

# Generate descriptions (RECOMMENDED - fast and effective)
python scripts/kg-quick-describe.py
```

**Proven Results**: A 2,555-node Chinese auto repair KG improved from 70.9 → 80.5 score (Good → Excellent) by:
1. Merging 370 duplicate nodes (5 sec)
2. Generating 2,555 descriptions via LLM (~20 min)

See `references/kg-repair.md` for:
- Duplicate node detection and merging
- LLM-powered description generation
- Isolated node handling
- Before/after metrics examples

### Critical: Rebuild Vector Index After Adding Descriptions

**Symptom**: RAG system returns "no relevant information found" even when data exists in graph.

**Cause**: Vector index was built before generating descriptions. Nodes have rich descriptions now but embeddings are stale.

**Fix**: Rebuild the vector index:
```bash
# Using the provided script
python scripts/rebuild-vector-index.py

# Or manually in Python
python
>>> from sentence_transformers import SentenceTransformer
>>> texts = [f"{n['type']}: {n['name']}。{n['description'][:100]}" for n in nodes]
>>> embeddings = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2').encode(texts)
>>> import numpy as np; np.save('embeddings.npy', embeddings)
```

**When to rebuild**:
- After batch-generating node descriptions
- After adding new properties to nodes
- After changing the text template/chunk strategy

### Quick Reference: Chinese Knowledge Graphs

```python
# Recommended setup for Chinese graphs
embedding_model = "BAAI/bge-small-zh-v1.5"  # or bge-large-zh for best quality
chunk_template = "{type}: {name}。{description}"  # Chinese punctuation
temperature = 0.3  # Lower for factual technical Q&A
```

## Key Decisions to Clarify with User
1. **RAG Type**: QA system, semantic search, or recommendation?
2. **Graph Schema**: What entities/relationships exist?
3. **Retrieval Strategy**: Vector-only, graph-only, or hybrid?
4. **LLM Backend**: OpenAI, DeepSeek, local model?
5. **Language**: Chinese graphs need BGE embedding models

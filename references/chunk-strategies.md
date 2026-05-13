# GraphRAG Chunk Strategies & Parameter Tuning

## "Chunk" Concept in GraphRAG

Unlike traditional RAG where chunks are fixed-size text segments, GraphRAG "chunks" are **semantic units based on graph nodes**.

### Strategy Comparison

| Strategy | Text Format | Use Case |
|----------|-------------|----------|
| Simple | `{type}: {name}` | Large graphs, fast retrieval |
| Standard | `{type}: {name}. {description}` | Balanced (recommended) |
| Rich | `{type}: {name}. {description}. Props: {props}` | Precise matching |
| Graph | Node + relation context | Complex queries needing structure |

### Implementation

```python
# Simple chunk
text = f"{node['type']}: {node['name']}"

# Standard chunk (recommended)
text = f"{node['type']}: {node['name']}。{node.get('description', '')}"

# Rich chunk with properties
text = f"{node['type']}: {node['name']}。{node.get('description', '')}。属性: {json.dumps(properties)}"

# Graph chunk with relations
context = " ".join([f"->{r['relation']}->{r['target']}" for r in relations])
text = f"{base_text} {context}"
```

## Embedding Model Selection

### For Chinese Knowledge Graphs

| Model | Dimensions | Speed | Chinese Quality |
|-------|------------|-------|-----------------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Fast | Medium |
| `BAAI/bge-small-zh-v1.5` | 512 | Medium | Good |
| `BAAI/bge-large-zh-v1.5` | 1024 | Slow | Excellent |

### Installation & Loading

```python
from sentence_transformers import SentenceTransformer

# Fast multilingual
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Chinese-optimized
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
```

## Key Parameters

### Vector Retrieval

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `top_k` | 10 | 5-20 | Higher = more recall, more noise |
| `min_score` | 0.3 | 0.1-0.5 | Higher = stricter filtering |
| `max_nodes` | 5000 | 1000-50000 | Nodes to index |

### LLM Generation

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `temperature` | 0.7 | 0.1-1.0 | Lower = more factual |
| `max_tokens` | 2000 | 500-4000 | Answer length limit |

### Graph Traversal

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `max_hops` | 2 | 1-3 | Relation depth |
| `max_results` | 20 | 10-100 | Query result limit |

## Tuning Recipes

### Speed-Optimized

```python
CONFIG = {
    "vector": {
        "model": "paraphrase-multilingual-MiniLM-L12-v2",
        "top_k": 5,
        "chunk_strategy": "simple"
    },
    "llm": {"temperature": 0.5}
}
```

### Accuracy-Optimized (Chinese)

```python
CONFIG = {
    "vector": {
        "model": "BAAI/bge-large-zh-v1.5",
        "top_k": 15,
        "chunk_strategy": "graph"
    },
    "llm": {"temperature": 0.1}
}
```

### Balanced

```python
CONFIG = {
    "vector": {
        "model": "BAAI/bge-small-zh-v1.5",
        "top_k": 10,
        "chunk_strategy": "standard"
    },
    "llm": {"temperature": 0.3}
}
```

## Chinese Knowledge Graph Tips

1. **Node labels**: Use Chinese labels directly in Cypher (`MATCH (n:故障代码)`)
2. **Text template**: Use Chinese punctuation (。instead of .)
3. **Embedding model**: Prefer BGE series for Chinese text
4. **LLM prompts**: Include Chinese schema examples for better Cypher generation

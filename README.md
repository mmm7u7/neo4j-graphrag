# Neo4j GraphRAG

Build Retrieval-Augmented Generation systems on Neo4j knowledge graphs.

## Quick Start

```bash
# 1. Start Neo4j
neo4j start

# 2. Install dependencies
pip install neo4j openai sentence-transformers numpy

# 3. Edit config
cp templates/config.yaml config.yaml
# Fill in your Neo4j password and LLM API key

# 4. Run
python templates/graphrag-deepseek.py
```

## Structure

```
├── templates/         # Config and implementation templates
├── scripts/           # KG evaluation, repair, and index tools
├── references/        # Detailed guides on chunk strategies, evaluation, repair
└── SKILL.md           # Full usage documentation
```

## License

MIT

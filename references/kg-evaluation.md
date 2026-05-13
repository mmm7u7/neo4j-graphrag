# Knowledge Graph Quality Evaluation

## Evaluation Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    KG Quality Assessment                     │
├─────────────────────────────────────────────────────────────┤
│  Data Layer          │  Structure Layer    │  Application   │
│  ───────────         │  ──────────────     │  ──────────    │
│  • Completeness      │  • Connectivity     │  • Query QA    │
│  • Accuracy          │  • Consistency      │  • RAG Quality │
│  • Coverage          │  • Hierarchy        │  • User Rating │
└─────────────────────────────────────────────────────────────┘
```

## Key Metrics

### 1. Completeness (数据层-完整性)

| Metric | Query | Good Threshold |
|--------|-------|----------------|
| Node count | `MATCH (n) RETURN count(n)` | Domain-dependent |
| Relation count | `MATCH ()-[r]->() RETURN count(r)` | 1.5-3x node count |
| Name fill rate | `MATCH (n) WHERE n.name IS NOT NULL` | >95% |
| Description fill rate | `MATCH (n) WHERE n.description IS NOT NULL` | >50% |
| Isolated nodes | `MATCH (n) WHERE NOT (n)--()` | <10% |

### 2. Coverage (数据层-覆盖度)

```cypher
-- Node type distribution
MATCH (n)
RETURN labels(n)[0] as label, count(n) as count
ORDER BY count DESC

-- Relation type distribution
MATCH ()-[r]->()
RETURN type(r) as type, count(r) as count
ORDER BY count DESC
```

### 3. Connectivity (结构层-连通性)

| Metric | Query | Ideal Range |
|--------|-------|-------------|
| Avg degree | `MATCH (n)-[r]-() WITH n, count(r) as d RETURN avg(d)` | 2-5 |
| Max degree | Same as above | <100 (avoid hubs) |
| Avg path length | Sample 100 pairs, shortestPath | 2-4 |

### 4. Consistency (结构层-一致性)

```cypher
-- Find duplicate node names (potential issue)
MATCH (n)
WHERE n.name IS NOT NULL
WITH n.name as name, count(n) as cnt
WHERE cnt > 1
RETURN name, cnt
ORDER BY cnt DESC

-- Find relation patterns
MATCH (a)-[r]->(b)
WHERE type(r) IN ['包含', '导致', '引起']
RETURN type(r), labels(a)[0], labels(b)[0], count(*)
```

## Scoring Formula

```python
# Completeness Score (0-100)
completeness = (
    name_fill_rate * 0.4 +
    description_fill_rate * 0.3 +
    (100 - isolated_rate) * 0.3
)

# Coverage Score (0-100)
coverage = min(100, 50 + label_types + relation_types)

# Connectivity Score (0-100)
connectivity = (
    50 if 2 <= avg_degree <= 5 else 30
) + (
    30 if max_degree < 100 else 10
)

# Query Success Rate (0-100)
query_rate = successful_queries / total_queries * 100

# Total Score
total = (completeness + coverage + connectivity + query_rate) / 4
```

## Quality Levels

| Score | Level | Action Needed |
|-------|-------|---------------|
| 80+ | Excellent ★★★★★ | Minor optimization |
| 60-79 | Good ★★★★ | Fill missing descriptions |
| 40-59 | Average ★★★ | Merge duplicates, add relations |
| <40 | Needs Work ★★ | Major data cleaning |

## Automated Evaluation Script

See `scripts/kg-evaluator.py` for a complete Python implementation that:
- Runs all metrics above
- Generates JSON report
- Provides improvement recommendations

## Manual Review Checklist

1. **Sample 20 random nodes** - Check if properties are correct
2. **Sample 20 relations** - Verify relationships are reasonable
3. **Domain coverage** - Compare with known entity lists (fault codes, vehicle models)
4. **Timeliness** - Check if knowledge is outdated
5. **QA testing** - Prepare 20 test questions, rate answers 1-5

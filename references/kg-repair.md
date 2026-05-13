# Knowledge Graph Repair Operations

## Common Issues & Fixes

### 1. Duplicate Nodes (重复节点)

**Symptom**: Same entity with different labels (e.g., "CAN总线" exists 11 times with labels: `通讯总线`, `总线`, `信号总线`, etc.)

**Detection**:
```cypher
MATCH (n)
WHERE n.name IS NOT NULL
WITH n.name as name, count(n) as cnt
WHERE cnt > 1
RETURN name, cnt
ORDER BY cnt DESC
```

**Fix Strategy**:
1. Select best label by priority
2. Keep one node, delete others
3. Migrate relations to kept node

**Implementation**:
```python
# Priority order for label selection
LABEL_PRIORITY = [
    "故障代码", "故障码", "故障", "故障现象",
    "部件", "系统", "控制单元", "模块",
    "设备", "工具", "参数", "实体"
]

def get_best_label(labels):
    for p in LABEL_PRIORITY:
        if p in labels:
            return p
    return labels[0]

# Merge duplicates in Cypher
def merge_duplicate_nodes(session, name):
    session.run("""
        MATCH (n {name: $name})
        WITH n ORDER BY id(n)
        WITH tail(collect(n)) as to_delete
        UNWIND to_delete as node
        DETACH DELETE node
        RETURN count(node) as deleted
    """, name=name)
```

**Note**: This simple approach deletes duplicates. For relation migration, use APOC's `apoc.refactor.mergeNodes()`.

### 2. Missing Descriptions (缺少描述)

**Symptom**: `description` property empty or missing on most nodes

**Detection**:
```cypher
MATCH (n)
WHERE n.name IS NOT NULL AND n.description IS NULL
RETURN count(n) as missing_descriptions
```

**Fix Strategy**: Use LLM to generate descriptions from node context

**Implementation**:
```python
from openai import OpenAI

def generate_description(llm, name, node_type, context):
    prompt = f"""为知识图谱节点生成简洁描述(30-50字)。

节点: {name}
类型: {node_type}
关系: {context}

描述:"""
    
    response = llm.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=80
    )
    return response.choices[0].message.content.strip()

# Get node context
def get_node_context(session, name):
    result = session.run("""
        MATCH (n {name: $name})-[r]-(related)
        RETURN type(r) as rel, labels(related)[0] as rtype, related.name as rname
        LIMIT 5
    """, name=name)
    return "\n".join([f"- {r['rel']}: {r['rname']}" for r in result])
```

**Rate Limiting**: Add `time.sleep(0.3)` between LLM calls to avoid API throttling.

### 3. Isolated Nodes (孤立节点)

**Symptom**: Nodes with no relations

**Detection**:
```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN n.name, labels(n)[0]
```

**Fix Strategies**:
1. Delete if truly irrelevant
2. Connect to related entities if valid
3. Use LLM to suggest connections

### 4. Relation Inconsistency (关系不一致)

**Symptom**: Same semantic relation with different names

**Example**: `包含`, `包含配件`, `包含部件` all mean "contains"

**Fix**: Standardize relation names:
```cypher
-- Rename inconsistent relations
MATCH ()-[r:包含配件]->()
CREATE (start)-[new:包含]->(end)
SET new = properties(r)
DELETE r
```

## Repair Workflow

```
1. Backup (optional but recommended)
   └─ Export to JSON: MATCH (n) RETURN n

2. Analyze
   └─ Run kg_evaluator.py for metrics

3. Prioritize
   ├─ High: Duplicate nodes, missing descriptions
   ├─ Medium: Isolated nodes, relation naming
   └─ Low: Property standardization

4. Execute
   ├─ Merge duplicates first (reduces node count)
   ├─ Generate descriptions (improves completeness)
   └─ Connect/remove isolated nodes

5. Verify
   └─ Run evaluator again, compare scores
```

## Automated Repair Script

See `scripts/kg-repair.py` for a complete implementation that:
- Detects and merges duplicate nodes
- Generates missing descriptions via LLM
- Provides progress logging
- Handles rate limiting

## Before/After Metrics Example (Real Session)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Nodes | 2,925 | 2,555 | -370 (merged) |
| Duplicate groups | 326 | 0 | ✓ Fixed |
| Description fill | 0% | 100% | +2,555 generated |
| Name fill | 100% | 100% | Maintained |
| **Completeness score** | 46.8 | **85.5** | +38.7 |
| **Total score** | 70.9 | **80.5** | +9.6 |
| **Level** | Good ★★★★ | **Excellent ★★★★★** | Upgraded |

### Time Estimate
- Merging 370 duplicates: ~5 seconds
- Generating 2,555 descriptions: ~15-20 minutes (with 0.1s delay between API calls)
- Total repair time: ~25 minutes

## Pitfalls

1. **Don't merge too aggressively** - Some duplicates may be intentional (same name, different contexts)
2. **Backup before batch operations** - Neo4j doesn't have undo
3. **Watch API rate limits** - LLM description generation needs throttling
4. **Test on small batch first** - Run with LIMIT 10 to verify logic

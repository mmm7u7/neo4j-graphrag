#!/usr/bin/env python3
"""
Knowledge Graph Repair Tool
Merges duplicate nodes and generates missing descriptions.

Usage:
    python kg-repair.py                    # Run all repairs
    python kg-repair.py --merge-only       # Only merge duplicates
    python kg-repair.py --describe-only    # Only generate descriptions
"""

import time
import argparse
from neo4j import GraphDatabase
from openai import OpenAI

# ============ CONFIGURATION ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "YOUR_PASSWORD"

# LLM Configuration (OpenAI-compatible API)
LLM_API_KEY = "YOUR_API_KEY"
LLM_BASE_URL = "https://api.deepseek.com/v1"  # or OpenAI, etc.
LLM_MODEL = "deepseek-chat"


class KGRepair:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.llm = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.stats = {"merged": 0, "described": 0}
    
    def close(self):
        self.driver.close()
    
    # ========== MERGE DUPLICATES ==========
    
    def merge_duplicates(self):
        """Merge nodes with same name, keeping one"""
        print("\n" + "="*60)
        print("Merging Duplicate Nodes")
        print("="*60)
        
        with self.driver.session() as session:
            # Get duplicate names
            result = session.run("""
                MATCH (n)
                WHERE n.name IS NOT NULL
                WITH n.name as name, count(n) as cnt
                WHERE cnt > 1
                RETURN name, cnt
                ORDER BY cnt DESC
            """)
            
            duplicates = list(result)
            print(f"Found {len(duplicates)} groups of duplicates\n")
            
            for record in duplicates:
                name = record["name"]
                
                # Delete all but first node (simple approach)
                merge_result = session.run("""
                    MATCH (n {name: $name})
                    WITH n ORDER BY id(n)
                    WITH tail(collect(n)) as to_delete
                    UNWIND to_delete as node
                    DETACH DELETE node
                    RETURN count(node) as deleted
                """, name=name).single()
                
                if merge_result and merge_result["deleted"] > 0:
                    self.stats["merged"] += merge_result["deleted"]
                    print(f"  ✓ '{name}': deleted {merge_result['deleted']} duplicates")
            
            print(f"\nTotal merged: {self.stats['merged']} nodes")
    
    # ========== GENERATE DESCRIPTIONS ==========
    
    def generate_descriptions(self, batch_size=50, max_total=100):
        """Generate missing descriptions using LLM"""
        print("\n" + "="*60)
        print("Generating Missing Descriptions")
        print("="*60)
        
        with self.driver.session() as session:
            # Count missing
            total_missing = session.run("""
                MATCH (n)
                WHERE n.name IS NOT NULL AND n.description IS NULL
                RETURN count(n) as c
            """).single()["c"]
            
            print(f"Nodes missing description: {total_missing}")
            
            if total_missing == 0:
                print("All nodes have descriptions!")
                return
            
            # Process in batches
            processed = 0
            while processed < min(total_missing, max_total):
                nodes = session.run(f"""
                    MATCH (n)
                    WHERE n.name IS NOT NULL AND n.description IS NULL
                    RETURN n.name as name, labels(n)[0] as type
                    SKIP {processed}
                    LIMIT {batch_size}
                """)
                
                for node in nodes:
                    name = node["name"]
                    node_type = node["type"]
                    
                    # Get context
                    context = session.run("""
                        MATCH (n {name: $name})-[r]-(related)
                        RETURN type(r) as rel, related.name as rname
                        LIMIT 5
                    """, name=name)
                    
                    ctx_str = "\n".join([
                        f"- {c['rel']}: {c['rname']}" 
                        for c in context
                    ])
                    
                    # Generate description
                    desc = self._generate_desc_llm(name, node_type, ctx_str)
                    
                    if desc:
                        session.run("""
                            MATCH (n {name: $name})
                            SET n.description = $desc
                        """, name=name, desc=desc)
                        
                        self.stats["described"] += 1
                        print(f"  [{self.stats['described']}] {name}: {desc[:40]}...")
                    
                    # Rate limiting
                    time.sleep(0.3)
                
                processed += batch_size
            
            print(f"\nTotal generated: {self.stats['described']} descriptions")
    
    def _generate_desc_llm(self, name, node_type, context):
        """Call LLM to generate description"""
        prompt = f"""为知识图谱节点生成简洁描述(30-50字)。

节点: {name}
类型: {node_type}
关系: {context if context else '无'}

描述:"""
        
        try:
            response = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  LLM error for '{name}': {e}")
            return None
    
    # ========== RUN ==========
    
    def run(self, merge=True, describe=True):
        """Run repairs"""
        print("\n" + "="*60)
        print("Knowledge Graph Repair Tool")
        print("="*60)
        
        start = time.time()
        
        if merge:
            self.merge_duplicates()
        
        if describe:
            self.generate_descriptions()
        
        elapsed = time.time() - start
        
        print("\n" + "="*60)
        print("Repair Complete")
        print("="*60)
        print(f"Nodes merged: {self.stats['merged']}")
        print(f"Descriptions generated: {self.stats['described']}")
        print(f"Time: {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KG Repair Tool")
    parser.add_argument("--merge-only", action="store_true", help="Only merge duplicates")
    parser.add_argument("--describe-only", action="store_true", help="Only generate descriptions")
    parser.add_argument("--max", type=int, default=100, help="Max descriptions to generate")
    
    args = parser.parse_args()
    
    repair = KGRepair()
    try:
        repair.run(
            merge=not args.describe_only,
            describe=not args.merge_only,
        )
        if args.max and not args.merge_only:
            repair.generate_descriptions(max_total=args.max)
    finally:
        repair.close()

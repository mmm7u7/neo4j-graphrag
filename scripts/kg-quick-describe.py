#!/usr/bin/env python3
"""
Quick Knowledge Graph Description Generator
Efficiently generates descriptions for all nodes missing them.
Uses OpenAI-compatible API (DeepSeek, OpenAI, etc.)

Usage:
    python kg-quick-describe.py
    
Configuration:
    Set NEO4J_PASSWORD and API_KEY below
"""

import time
from neo4j import GraphDatabase
from openai import OpenAI

# ============ CONFIGURATION ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "YOUR_NEO4J_PASSWORD"

API_KEY = "YOUR_API_KEY"
API_BASE_URL = "https://api.deepseek.com/v1"  # or OpenAI URL
API_MODEL = "deepseek-chat"

BATCH_SIZE = 300       # Nodes per batch
MAX_TOKENS = 50        # Max response tokens
DELAY = 0.1            # Delay between API calls (avoid rate limits)


def generate_descriptions():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    llm = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    
    total_generated = 0
    
    try:
        with driver.session() as session:
            # Get count of missing descriptions
            total_missing = session.run("""
                MATCH (n)
                WHERE n.name IS NOT NULL AND n.description IS NULL
                RETURN count(n) as total
            """).single()["total"]
            
            print(f"Nodes missing description: {total_missing}")
            
            if total_missing == 0:
                print("All nodes have descriptions!")
                return
            
            while True:
                # Get batch of nodes
                nodes = session.run(f"""
                    MATCH (n)
                    WHERE n.name IS NOT NULL AND n.description IS NULL
                    RETURN n.name as name, labels(n)[0] as type
                    LIMIT {BATCH_SIZE}
                """)
                
                node_list = list(nodes)
                if not node_list:
                    break
                
                batch_count = 0
                for node in node_list:
                    name = node["name"]
                    node_type = node["type"]
                    
                    # Generate description
                    prompt = f"汽修知识图谱节点'{name}'(类型:{node_type})的简短描述(30字内):"
                    
                    try:
                        resp = llm.chat.completions.create(
                            model=API_MODEL,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=MAX_TOKENS
                        )
                        desc = resp.choices[0].message.content.strip()
                        
                        # Write to database
                        session.run(
                            "MATCH (n {name: $n}) SET n.description = $d",
                            n=name, d=desc
                        )
                        
                        batch_count += 1
                        total_generated += 1
                        
                        if total_generated % 50 == 0:
                            progress = total_generated / total_missing * 100
                            print(f"Progress: {total_generated}/{total_missing} ({progress:.1f}%)")
                        
                    except Exception as e:
                        if "rate limit" in str(e).lower():
                            print("Rate limited, waiting 30s...")
                            time.sleep(30)
                        pass
                    
                    time.sleep(DELAY)
                
                print(f"Batch complete: {batch_count} descriptions")
                
                # Check if done
                remaining = session.run("""
                    MATCH (n)
                    WHERE n.name IS NOT NULL AND n.description IS NULL
                    RETURN count(n) as count
                """).single()["count"]
                
                if remaining == 0:
                    break
                
                print(f"Remaining: {remaining}")
    
    finally:
        driver.close()
    
    print(f"\nTotal generated: {total_generated}")


if __name__ == "__main__":
    generate_descriptions()

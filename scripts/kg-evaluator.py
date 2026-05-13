#!/usr/bin/env python3
"""
Knowledge Graph Quality Evaluator
Evaluates completeness, coverage, connectivity, and query quality.

Usage:
    python kg-evaluator.py
"""

import json
import time
from neo4j import GraphDatabase

# ============ CONFIGURATION ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "YOUR_PASSWORD"


class KGEvaluator:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.results = {}
    
    def close(self):
        self.driver.close()
    
    def query(self, cypher, parameters=None):
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]
    
    def evaluate_completeness(self):
        """Evaluate data completeness"""
        node_count = self.query("MATCH (n) RETURN count(n) as c")[0]['c']
        rel_count = self.query("MATCH ()-[r]->() RETURN count(r) as c")[0]['c']
        
        nodes_with_name = self.query(
            "MATCH (n) WHERE n.name IS NOT NULL RETURN count(n) as c"
        )[0]['c']
        nodes_with_desc = self.query(
            "MATCH (n) WHERE n.description IS NOT NULL RETURN count(n) as c"
        )[0]['c']
        
        isolated = self.query(
            "MATCH (n) WHERE NOT (n)--() RETURN count(n) as c"
        )[0]['c']
        
        return {
            "node_count": node_count,
            "relation_count": rel_count,
            "name_fill_rate": nodes_with_name / node_count * 100 if node_count else 0,
            "desc_fill_rate": nodes_with_desc / node_count * 100 if node_count else 0,
            "isolated_nodes": isolated,
            "isolated_rate": isolated / node_count * 100 if node_count else 0
        }
    
    def evaluate_coverage(self):
        """Evaluate type coverage"""
        labels = self.query("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        rels = self.query("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        
        label_count = self.query(
            "CALL db.labels() YIELD label RETURN count(label) as c"
        )[0]['c']
        rel_type_count = self.query(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN count(relationshipType) as c"
        )[0]['c']
        
        return {
            "label_count": label_count,
            "rel_type_count": rel_type_count,
            "label_distribution": labels[:20],
            "rel_distribution": rels[:20]
        }
    
    def evaluate_connectivity(self):
        """Evaluate graph connectivity"""
        degree_stats = self.query("""
            MATCH (n)-[r]-()
            WITH n, count(r) as degree
            RETURN avg(degree) as avg, max(degree) as max, min(degree) as min
        """)[0]
        
        hubs = self.query("""
            MATCH (n)-[r]-()
            WITH n, count(r) as degree
            ORDER BY degree DESC
            LIMIT 10
            RETURN n.name as name, labels(n)[0] as type, degree
        """)
        
        duplicates = self.query("""
            MATCH (n)
            WHERE n.name IS NOT NULL
            WITH n.name as name, count(n) as cnt
            WHERE cnt > 1
            RETURN count(*) as dup_groups, sum(cnt) as total
        """)[0]
        
        return {
            "avg_degree": degree_stats['avg'],
            "max_degree": degree_stats['max'],
            "hub_nodes": hubs,
            "duplicate_groups": duplicates.get('dup_groups', 0)
        }
    
    def calculate_scores(self):
        """Calculate composite scores"""
        c = self.results.get('completeness', {})
        cv = self.results.get('coverage', {})
        cn = self.results.get('connectivity', {})
        
        # Completeness (0-100)
        completeness_score = (
            c.get('name_fill_rate', 0) * 0.4 +
            c.get('desc_fill_rate', 0) * 0.3 +
            (100 - c.get('isolated_rate', 0)) * 0.3
        )
        
        # Coverage (0-100)
        coverage_score = min(100, 50 + cv.get('label_count', 0) * 0.2)
        
        # Connectivity (0-100)
        avg_deg = cn.get('avg_degree', 0)
        connectivity_score = 50 if 2 <= avg_deg <= 5 else 30
        if cn.get('max_degree', 0) < 100:
            connectivity_score += 30
        else:
            connectivity_score += 10
        
        # Deduct for duplicates
        dup_penalty = min(20, cn.get('duplicate_groups', 0) * 0.5)
        connectivity_score -= dup_penalty
        
        # Total
        total = (completeness_score + coverage_score + connectivity_score) / 3
        
        return {
            "completeness": round(completeness_score, 1),
            "coverage": round(coverage_score, 1),
            "connectivity": round(max(0, connectivity_score), 1),
            "total": round(total, 1)
        }
    
    def run(self):
        """Run full evaluation"""
        print("="*60)
        print("Knowledge Graph Quality Evaluation")
        print("="*60)
        
        self.results['completeness'] = self.evaluate_completeness()
        self.results['coverage'] = self.evaluate_coverage()
        self.results['connectivity'] = self.evaluate_connectivity()
        self.results['scores'] = self.calculate_scores()
        
        # Print results
        print(f"\nNodes: {self.results['completeness']['node_count']}")
        print(f"Relations: {self.results['completeness']['relation_count']}")
        print(f"Name fill: {self.results['completeness']['name_fill_rate']:.1f}%")
        print(f"Desc fill: {self.results['completeness']['desc_fill_rate']:.1f}%")
        print(f"Isolated: {self.results['completeness']['isolated_nodes']} ({self.results['completeness']['isolated_rate']:.1f}%)")
        print(f"Duplicate groups: {self.results['connectivity']['duplicate_groups']}")
        
        print("\n" + "="*60)
        print("Scores")
        print("="*60)
        for k, v in self.results['scores'].items():
            print(f"  {k}: {v}/100")
        
        # Determine level
        total = self.results['scores']['total']
        if total >= 80:
            level = "Excellent ★★★★★"
        elif total >= 60:
            level = "Good ★★★★"
        elif total >= 40:
            level = "Average ★★★"
        else:
            level = "Needs Work ★★"
        print(f"\n  Level: {level}")
        
        return self.results
    
    def save_report(self, filename="kg_evaluation_report.json"):
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            **self.results
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nReport saved: {filename}")


if __name__ == "__main__":
    evaluator = KGEvaluator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        evaluator.run()
        evaluator.save_report()
    finally:
        evaluator.close()

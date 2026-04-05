"""
Research Memory System for Hexamind
Implements semantic memory across research sessions with knowledge graph
"""

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import re


@dataclass
class ResearchNode:
    """A node in the research knowledge graph"""
    id: str
    topic: str
    content: str
    session_id: str
    timestamp: str
    confidence_score: float
    sources: List[str]
    related_topics: List[str]
    keywords: List[str]
    node_type: str  # "claim", "finding", "methodology", "source"


@dataclass
class ResearchEdge:
    """An edge connecting research nodes"""
    source_id: str
    target_id: str
    relationship: str  # "supports", "contradicts", "extends", "relates_to"
    strength: float
    evidence: str


@dataclass
class ResearchSession:
    """Complete research session with memory integration"""
    session_id: str
    query: str
    timestamp: str
    nodes: List[ResearchNode]
    edges: List[ResearchEdge]
    quality_metrics: Dict
    key_findings: List[str]


class ResearchMemory:
    """Semantic memory system for cross-session research intelligence"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(__file__).parent / ".data" / "research_memory.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.nodes: Dict[str, ResearchNode] = {}
        self.edges: List[ResearchEdge] = []
        self.sessions: Dict[str, ResearchSession] = {}
        
        self._load_memory()
    
    def _load_memory(self):
        """Load research memory from storage"""
        if not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            
            # Load nodes
            for node_data in data.get("nodes", []):
                node = ResearchNode(**node_data)
                self.nodes[node.id] = node
            
            # Load edges
            for edge_data in data.get("edges", []):
                edge = ResearchEdge(**edge_data)
                self.edges.append(edge)
            
            # Load sessions
            for session_data in data.get("sessions", []):
                session = ResearchSession(**session_data)
                self.sessions[session.session_id] = session
                
        except Exception as e:
            print(f"Error loading research memory: {e}")
    
    def _save_memory(self):
        """Save research memory to storage"""
        data = {
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [asdict(edge) for edge in self.edges],
            "sessions": [asdict(session) for session in self.sessions.values()],
            "last_updated": datetime.now().isoformat()
        }
        
        temp_path = self.storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(self.storage_path)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from research text"""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        # Filter out common words
        stop_words = {
            "this", "that", "with", "from", "they", "have", "been", "their", "would", "could",
            "should", "will", "research", "study", "analysis", "findings", "results", "data"
        }
        
        keywords = [word for word in words if word not in stop_words]
        
        # Return top keywords by frequency
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, _ in word_counts.most_common(10)]
    
    def _find_related_nodes(self, topic: str, keywords: List[str]) -> List[ResearchNode]:
        """Find existing nodes related to current research"""
        topic_lower = topic.lower()
        keyword_set = set(keywords)
        
        related_nodes = []
        for node in self.nodes.values():
            # Topic similarity
            topic_match = any(word in node.topic.lower() for word in topic_lower.split())
            
            # Keyword overlap
            keyword_overlap = len(set(node.keywords) & keyword_set)
            
            # Calculate relevance score
            relevance_score = 0
            if topic_match:
                relevance_score += 0.5
            relevance_score += keyword_overlap * 0.1
            
            if relevance_score > 0.3:  # Threshold for relevance
                related_nodes.append((node, relevance_score))
        
        # Sort by relevance and return top matches
        related_nodes.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in related_nodes[:5]]
    
    def _create_research_node(self, content: str, session_id: str, node_type: str = "finding") -> ResearchNode:
        """Create a new research node from content"""
        # Generate unique ID
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        node_id = f"{node_type}_{content_hash}_{int(datetime.now().timestamp())}"
        
        # Extract topic (simplified - would use NLP in production)
        lines = content.split('\n')
        topic_line = next((line for line in lines if line.strip() and not line.startswith('#')), content[:100])
        topic = topic_line[:100].strip()
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        return ResearchNode(
            id=node_id,
            topic=topic,
            content=content,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            confidence_score=0.8,  # Would be calculated from actual confidence scoring
            sources=[],  # Would be extracted from actual sources
            related_topics=[],
            keywords=keywords,
            node_type=node_type
        )
    
    def _create_edges_between_nodes(self, new_node: ResearchNode, related_nodes: List[ResearchNode]):
        """Create edges between new node and related existing nodes"""
        for existing_node in related_nodes:
            # Calculate relationship strength based on keyword overlap
            keyword_overlap = len(set(new_node.keywords) & set(existing_node.keywords))
            strength = min(keyword_overlap / 5, 1.0)  # Normalize to 0-1
            
            if strength > 0.2:  # Only create edges for meaningful relationships
                # Determine relationship type
                relationship = "relates_to"
                if "contradict" in new_node.content.lower() or "however" in new_node.content.lower():
                    relationship = "contradicts"
                elif "support" in new_node.content.lower() or "confirm" in new_node.content.lower():
                    relationship = "supports"
                elif "extend" in new_node.content.lower() or "build" in new_node.content.lower():
                    relationship = "extends"
                
                edge = ResearchEdge(
                    source_id=new_node.id,
                    target_id=existing_node.id,
                    relationship=relationship,
                    strength=strength,
                    evidence=f"Keyword overlap: {keyword_overlap} terms"
                )
                self.edges.append(edge)
    
    def store_research_session(self, 
                            session_id: str,
                            query: str,
                            research_output: str,
                            quality_metrics: Dict,
                            sources: List[str] = None) -> Dict:
        """Store a complete research session in memory"""
        
        # Create main research node
        main_node = self._create_research_node(research_output, session_id, "finding")
        
        # Find related existing nodes
        related_nodes = self._find_related_nodes(query, main_node.keywords)
        
        # Create edges to related nodes
        self._create_edges_between_nodes(main_node, related_nodes)
        
        # Store the node
        self.nodes[main_node.id] = main_node
        
        # Extract key findings (simplified)
        key_findings = []
        lines = research_output.split('\n')
        for line in lines:
            if any(indicator in line.lower() for indicator in ['conclusion:', 'finding:', 'result:', 'therefore']):
                key_findings.append(line.strip())
        key_findings = key_findings[:5]  # Top 5 findings
        
        # Create session record
        session = ResearchSession(
            session_id=session_id,
            query=query,
            timestamp=datetime.now().isoformat(),
            nodes=[main_node],
            edges=[edge for edge in self.edges if edge.source_id == main_node.id],
            quality_metrics=quality_metrics,
            key_findings=key_findings
        )
        
        self.sessions[session_id] = session
        self._save_memory()
        
        return {
            "session_stored": True,
            "node_id": main_node.id,
            "related_nodes_found": len(related_nodes),
            "edges_created": len(session.edges),
            "key_findings": len(key_findings)
        }
    
    def query_memory(self, query: str, limit: int = 10) -> Dict:
        """Query research memory for relevant information"""
        
        query_keywords = self._extract_keywords(query)
        query_lower = query.lower()
        
        # Find matching nodes
        matching_nodes = []
        for node in self.nodes.values():
            # Calculate relevance score
            relevance_score = 0
            
            # Topic matching
            if any(word in node.topic.lower() for word in query_lower.split()):
                relevance_score += 0.4
            
            # Keyword matching
            keyword_overlap = len(set(node.keywords) & set(query_keywords))
            relevance_score += keyword_overlap * 0.1
            
            # Content matching (simplified)
            content_matches = sum(1 for word in query_keywords if word in node.content.lower())
            relevance_score += content_matches * 0.05
            
            # Recency bonus (more recent = slightly higher score)
            node_date = datetime.fromisoformat(node.timestamp)
            days_old = (datetime.now() - node_date).days
            recency_bonus = max(0, 1 - (days_old / 365))  # Decay over year
            relevance_score += recency_bonus * 0.1
            
            if relevance_score > 0.2:  # Threshold
                matching_nodes.append((node, relevance_score))
        
        # Sort by relevance and limit
        matching_nodes.sort(key=lambda x: x[1], reverse=True)
        top_nodes = matching_nodes[:limit]
        
        # Get related edges
        node_ids = [node.id for node, _ in top_nodes]
        related_edges = [edge for edge in self.edges 
                       if edge.source_id in node_ids or edge.target_id in node_ids]
        
        return {
            "query": query,
            "matching_nodes": [
                {
                    "node_id": node.id,
                    "topic": node.topic,
                    "content_preview": node.content[:200] + "..." if len(node.content) > 200 else node.content,
                    "confidence_score": node.confidence_score,
                    "session_id": node.session_id,
                    "timestamp": node.timestamp,
                    "keywords": node.keywords,
                    "relevance_score": round(score, 3),
                    "node_type": node.node_type
                } for node, score in top_nodes
            ],
            "related_edges": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relationship": edge.relationship,
                    "strength": edge.strength,
                    "evidence": edge.evidence
                } for edge in related_edges
            ],
            "total_matches": len(matching_nodes),
            "query_timestamp": datetime.now().isoformat()
        }
    
    def get_research_graph(self, topic: str = None, depth: int = 2) -> Dict:
        """Get research knowledge graph for visualization"""
        
        if topic:
            # Get topic-specific graph
            keywords = self._extract_keywords(topic)
            relevant_nodes = self._find_related_nodes(topic, keywords)
            node_ids = [node.id for node in relevant_nodes]
            
            # Get edges for these nodes
            edges = [edge for edge in self.edges 
                    if edge.source_id in node_ids or edge.target_id in node_ids]
            
            nodes = relevant_nodes
        else:
            # Get full graph (limited to recent nodes)
            recent_cutoff = datetime.now() - timedelta(days=30)
            nodes = [node for node in self.nodes.values() 
                    if datetime.fromisoformat(node.timestamp) > recent_cutoff]
            edges = self.edges
        
        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.topic[:50] + "..." if len(node.topic) > 50 else node.topic,
                    "confidence": node.confidence_score,
                    "type": node.node_type,
                    "session_id": node.session_id,
                    "keywords": node.keywords[:5],
                    "timestamp": node.timestamp
                } for node in nodes
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship,
                    "strength": edge.strength,
                    "label": f"{edge.relationship} ({edge.strength:.2f})"
                } for edge in edges
            ],
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "graph_depth": depth,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def get_cross_session_insights(self, query: str) -> Dict:
        """Generate insights across multiple research sessions"""
        
        # Get relevant sessions
        relevant_sessions = []
        query_keywords = set(self._extract_keywords(query))
        
        for session in self.sessions.values():
            session_keywords = set()
            for node in session.nodes:
                session_keywords.update(node.keywords)
            
            overlap = len(query_keywords & session_keywords)
            if overlap > 0:
                relevant_sessions.append((session, overlap))
        
        relevant_sessions.sort(key=lambda x: x[1], reverse=True)
        
        # Generate insights
        insights = []
        if len(relevant_sessions) >= 2:
            # Find common themes
            all_findings = []
            for session, _ in relevant_sessions[:5]:
                all_findings.extend(session.key_findings)
            
            # Find patterns (simplified)
            common_themes = []
            for finding in all_findings:
                if finding.lower() in [f.lower() for f in common_themes]:
                    continue
                similar_count = sum(1 for f in all_findings 
                                  if finding.lower() in f.lower() or f.lower() in finding.lower())
                if similar_count > 1:
                    common_themes.append(finding)
            
            if common_themes:
                insights.append({
                    "type": "common_themes",
                    "insight": f"Found {len(common_themes)} recurring themes across related research",
                    "themes": common_themes[:3]
                })
            
            # Find contradictions
            contradictions = []
            for i, (session1, _) in enumerate(relevant_sessions[:3]):
                for session2, _ in relevant_sessions[i+1:4]:
                    # Simplified contradiction detection
                    for finding1 in session1.key_findings:
                        for finding2 in session2.key_findings:
                            if ("however" in finding1.lower() or "but" in finding1.lower()) and \
                               finding1.lower() != finding2.lower():
                                contradictions.append({
                                    "session1": session1.session_id,
                                    "session2": session2.session_id,
                                    "finding1": finding1,
                                    "finding2": finding2
                                })
            
            if contradictions:
                insights.append({
                    "type": "contradictions",
                    "insight": f"Found {len(contradictions)} potential contradictions across sessions",
                    "contradictions": contradictions[:2]
                })
        
        return {
            "query": query,
            "relevant_sessions": len(relevant_sessions),
            "insights": insights,
            "recommendations": [
                "Review related sessions for additional context",
                "Consider contradictions when forming conclusions",
                "Leverage common themes for stronger arguments"
            ]
        }


# Global memory instance
research_memory = ResearchMemory()


def store_session(session_id: str, query: str, output: str, metrics: Dict, sources: List[str] = None) -> Dict:
    """Public interface for storing research sessions"""
    return research_memory.store_research_session(session_id, query, output, metrics, sources)


def query_research_memory(query: str, limit: int = 10) -> Dict:
    """Public interface for querying research memory"""
    return research_memory.query_memory(query, limit)


def get_research_graph(topic: str = None, depth: int = 2) -> Dict:
    """Public interface for getting research graph"""
    return research_memory.get_research_graph(topic, depth)

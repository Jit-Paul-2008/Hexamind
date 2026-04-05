"""
Advanced Features API Endpoints for Hexamind
Provides REST endpoints for cost-aware routing, confidence scoring, research memory, and collaboration
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
import json

from cost_aware_routing import route_query, estimate_query_cost
from confidence_scoring import score_research_confidence
from research_memory import query_research_memory, get_research_graph
from collaboration import create_collaboration_session, access_collaboration_session, create_context_handoff


router = APIRouter(prefix="/api/advanced", tags=["advanced"])


class CostEstimationRequest(BaseModel):
    query: str
    agent_type: str
    cost_mode: Optional[str] = "balanced"


class ConfidenceScoringRequest(BaseModel):
    research_text: str
    sources: List[str]


class MemoryQueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


class CollaborationCreateRequest(BaseModel):
    original_session_id: str
    owner_id: str
    title: str
    description: str
    research_data: Dict
    permission_level: Optional[str] = "read_only"
    expires_hours: Optional[int] = 168


class CollaborationAccessRequest(BaseModel):
    access_code: str
    user_id: str


class ContextHandoffRequest(BaseModel):
    session_id: str
    research_data: Dict
    target_user: Optional[str] = None
    message: Optional[str] = ""


@router.post("/cost/estimate")
async def estimate_cost_endpoint(request: CostEstimationRequest):
    """Estimate cost and performance for query routing"""
    try:
        estimation = estimate_query_cost(request.query, request.agent_type)
        return {
            "status": "success",
            "estimation": estimation,
            "recommendations": [
                f"Use {estimation['model']} for optimal cost-quality balance",
                f"Estimated cost: ${estimation['estimated_cost_usd']:.4f}",
                f"Estimated time: {estimation['estimated_time_seconds']:.1f}s"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cost estimation failed: {str(e)}")


@router.post("/cost/route")
async def route_query_endpoint(request: CostEstimationRequest):
    """Get optimal model routing for query"""
    try:
        optimal_model = route_query(request.query, request.agent_type, request.cost_mode)
        estimation = estimate_query_cost(request.query, request.agent_type)
        
        return {
            "status": "success",
            "optimal_model": optimal_model,
            "query_complexity": estimation.get("complexity"),
            "cost_estimate": estimation,
            "routing_reasoning": f"Selected {optimal_model} based on query complexity and agent requirements"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query routing failed: {str(e)}")


@router.post("/confidence/score")
async def score_confidence_endpoint(request: ConfidenceScoringRequest):
    """Score confidence for research output"""
    try:
        confidence_analysis = score_research_confidence(request.research_text, request.sources)
        
        return {
            "status": "success",
            "confidence_analysis": confidence_analysis,
            "summary": {
                "overall_confidence": confidence_analysis["overall_confidence"],
                "total_claims": confidence_analysis["total_claims"],
                "high_confidence_rate": confidence_analysis["verification_rate"],
                "risk_level": "low" if confidence_analysis["overall_confidence"] >= 0.8 else "medium" if confidence_analysis["overall_confidence"] >= 0.6 else "high"
            },
            "actionable_insights": confidence_analysis["recommendations"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confidence scoring failed: {str(e)}")


@router.post("/memory/query")
async def query_memory_endpoint(request: MemoryQueryRequest):
    """Query research memory for relevant information"""
    try:
        memory_results = query_research_memory(request.query, request.limit)
        
        return {
            "status": "success",
            "query": request.query,
            "memory_results": memory_results,
            "insights": {
                "total_matches": memory_results["total_matches"],
                "has_related_research": memory_results["total_matches"] > 0,
                "confidence_range": [
                    min(node["relevance_score"] for node in memory_results["matching_nodes"]),
                    max(node["relevance_score"] for node in memory_results["matching_nodes"])
                ] if memory_results["matching_nodes"] else [0, 0]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")


@router.get("/memory/graph")
async def get_memory_graph_endpoint(topic: Optional[str] = None, depth: Optional[int] = 2):
    """Get research knowledge graph for visualization"""
    try:
        graph_data = get_research_graph(topic, depth)
        
        return {
            "status": "success",
            "graph_data": graph_data,
            "visualization_hints": {
                "node_size_property": "confidence",
                "edge_thickness_property": "strength",
                "node_color_property": "type",
                "layout_algorithm": "force_directed"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph generation failed: {str(e)}")


@router.post("/collaboration/create")
async def create_collaboration_endpoint(request: CollaborationCreateRequest):
    """Create a new collaboration session"""
    try:
        collaboration = create_collaboration_session(
            request.original_session_id,
            request.owner_id,
            request.title,
            request.description,
            request.research_data,
            request.permission_level
        )
        
        return {
            "status": "success",
            "collaboration": collaboration,
            "next_steps": [
                f"Share this URL: {collaboration['share_url']}",
                f"Access code: {collaboration['access_code']}",
                f"Session expires: {collaboration['expires_at']}"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collaboration creation failed: {str(e)}")


@router.post("/collaboration/access")
async def access_collaboration_endpoint(request: CollaborationAccessRequest):
    """Access a collaboration session"""
    try:
        session_data = access_collaboration_session(request.access_code, request.user_id)
        
        if "error" in session_data:
            raise HTTPException(status_code=400, detail=session_data["error"])
        
        return {
            "status": "success",
            "session_accessed": True,
            "session_data": session_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collaboration access failed: {str(e)}")


@router.post("/collaboration/handoff")
async def create_handoff_endpoint(request: ContextHandoffRequest):
    """Create a context handoff for another researcher"""
    try:
        handoff = create_context_handoff(
            request.session_id,
            request.research_data,
            request.target_user,
            request.message
        )
        
        return {
            "status": "success",
            "handoff_created": handoff,
            "handoff_summary": {
                "snapshot_id": handoff["snapshot_id"],
                "collaboration_url": handoff["collaboration_session"]["share_url"],
                "expires_in_hours": 72
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context handoff failed: {str(e)}")


@router.get("/features/status")
async def get_features_status():
    """Get status of all advanced features"""
    return {
        "status": "success",
        "features": {
            "cost_aware_routing": {
                "enabled": True,
                "description": "Smart model selection based on query complexity and cost optimization",
                "capabilities": ["Query complexity analysis", "Cost estimation", "Optimal model routing"]
            },
            "confidence_scoring": {
                "enabled": True,
                "description": "Per-claim confidence scoring with explainable reasoning",
                "capabilities": ["Claim extraction", "Confidence assessment", "Actionable recommendations"]
            },
            "research_memory": {
                "enabled": True,
                "description": "Semantic memory across research sessions with knowledge graph",
                "capabilities": ["Cross-session memory", "Knowledge graph", "Context retrieval"]
            },
            "collaboration": {
                "enabled": True,
                "description": "Session sharing and context handoff between researchers",
                "capabilities": ["Session sharing", "Context preservation", "Real-time collaboration"]
            }
        },
        "integration_status": "fully_integrated"
    }


@router.get("/demo/complete_research_tool")
async def demo_complete_research_tool():
    """Demonstrate all 8 research tool parameters working together"""
    
    demo_query = "quantum computing applications in drug discovery"
    
    # 1. Cost-Aware Routing
    cost_estimate = estimate_query_cost(demo_query, "advocate")
    optimal_model = route_query(demo_query, "advocate")
    
    # 2. Research Memory (query existing research)
    memory_results = query_research_memory(demo_query, 5)
    
    # 3. Confidence Scoring (demo with sample text)
    sample_research = """
    Quantum computing shows significant promise for drug discovery applications.
    Research indicates that quantum algorithms can accelerate molecular simulations.
    However, current quantum hardware limitations constrain practical applications.
    Multiple studies suggest hybrid quantum-classical approaches are most promising.
    """
    confidence_analysis = score_research_confidence(sample_research, ["S1", "S2", "S3", "S4"])
    
    # 4. Collaboration (demo session)
    demo_collaboration = create_collaboration_session(
        "demo_session",
        "demo_user",
        "Quantum Computing Research Demo",
        "Demonstration of complete research tool capabilities",
        {"query": demo_query, "findings": ["Quantum advantage", "Hardware limitations"]},
        "read_only"
    )
    
    return {
        "title": "Hexamind: Complete Research Tool Demonstration",
        "subtitle": "All 8 Research Tool Parameters Working in Harmony",
        "query": demo_query,
        "demonstration": {
            "1_reasoning_transparency": {
                "status": "implemented",
                "description": "Multi-agent pipeline shows Advocate↔Skeptic↔Synthesiser reasoning chains",
                "current_implementation": "5-agent adversarial system with full transparency"
            },
            "2_adversarial_stress_testing": {
                "status": "implemented", 
                "description": "Built-in Skeptic agent deliberately challenges assumptions",
                "current_implementation": "Automated risk assessment and failure mode analysis"
            },
            "3_structured_output": {
                "status": "implemented",
                "description": "IMRaD format research paper generator",
                "current_implementation": "Academic paper structure with proper sections"
            },
            "4_multi_perspective_synthesis": {
                "status": "implemented",
                "description": "Multiple agents debate and integrate competing perspectives",
                "current_implementation": "5-agent synthesis with conflict resolution"
            },
            "5_cost_aware_routing": {
                "status": "implemented",
                "demonstration": {
                    "query_complexity": cost_estimate["complexity"],
                    "optimal_model": optimal_model,
                    "estimated_cost": f"${cost_estimate['estimated_cost_usd']:.4f}",
                    "quality_score": cost_estimate["quality_score"]
                }
            },
            "6_memory_across_sessions": {
                "status": "implemented",
                "demonstration": {
                    "related_research_found": memory_results["total_matches"],
                    "memory_nodes": len(memory_results["matching_nodes"]),
                    "cross_session_insights": "Semantic connections maintained across sessions"
                }
            },
            "7_actionable_confidence_scoring": {
                "status": "implemented",
                "demonstration": {
                    "overall_confidence": confidence_analysis["overall_confidence"],
                    "claims_analyzed": confidence_analysis["total_claims"],
                    "high_confidence_rate": f"{confidence_analysis['verification_rate']:.1%}",
                    "recommendations": confidence_analysis["recommendations"][:2]
                }
            },
            "8_collaboration_without_context_loss": {
                "status": "implemented",
                "demonstration": {
                    "collaboration_url": demo_collaboration["share_url"],
                    "access_code": demo_collaboration["access_code"],
                    "context_preserved": "Full research context with agent states and reasoning chains"
                }
            }
        },
        "competitive_advantage": {
            "unlike_perplexity": "Full reasoning transparency, not just answers",
            "unlike_elicit": "Multi-agent synthesis, not just data extraction", 
            "unlike_chatgpt": "Adversarial stress-testing, not just confident responses",
            "unlike_consensus": "Cost-aware routing, not one-size-fits-all models"
        },
        "market_positioning": "The only research tool that combines all 8 critical parameters for serious research work"
    }

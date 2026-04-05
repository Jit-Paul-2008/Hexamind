"""
Collaboration System for Hexamind
Implements session sharing and context handoff between researchers
"""

import json
import secrets
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from enum import Enum


class PermissionLevel(Enum):
    READ_ONLY = "read_only"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"


@dataclass
class CollaborationSession:
    """A collaborative research session"""
    session_id: str
    original_session_id: str
    owner_id: str
    title: str
    description: str
    created_at: str
    expires_at: str
    permission_level: PermissionLevel
    research_data: Dict
    comments: List[Dict]
    contributors: List[str]
    is_active: bool


@dataclass
class ContextSnapshot:
    """Snapshot of research context for handoff"""
    snapshot_id: str
    session_id: str
    timestamp: str
    query: str
    agent_states: Dict
    findings: List[str]
    sources: List[str]
    confidence_scores: Dict
    reasoning_chains: Dict
    metadata: Dict


class CollaborationManager:
    """Manages research collaboration and context sharing"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(__file__).parent / ".data" / "collaboration.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.collaboration_sessions: Dict[str, CollaborationSession] = {}
        self.context_snapshots: Dict[str, ContextSnapshot] = {}
        self.access_codes: Dict[str, str] = {}  # access_code -> session_id
        
        self._load_data()
    
    def _load_data(self):
        """Load collaboration data from storage"""
        if not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            
            # Load collaboration sessions
            for session_data in data.get("collaboration_sessions", []):
                session_data["permission_level"] = PermissionLevel(session_data["permission_level"])
                session = CollaborationSession(**session_data)
                self.collaboration_sessions[session.session_id] = session
            
            # Load context snapshots
            for snapshot_data in data.get("context_snapshots", []):
                snapshot = ContextSnapshot(**snapshot_data)
                self.context_snapshots[snapshot.snapshot_id] = snapshot
            
            # Load access codes
            self.access_codes = data.get("access_codes", {})
            
        except Exception as e:
            print(f"Error loading collaboration data: {e}")
    
    def _save_data(self):
        """Save collaboration data to storage"""
        data = {
            "collaboration_sessions": [
                {**asdict(session), "permission_level": session.permission_level.value}
                for session in self.collaboration_sessions.values()
            ],
            "context_snapshots": [asdict(snapshot) for snapshot in self.context_snapshots.values()],
            "access_codes": self.access_codes,
            "last_updated": datetime.now().isoformat()
        }
        
        temp_path = self.storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(self.storage_path)
    
    def _generate_access_code(self) -> str:
        """Generate secure access code"""
        return secrets.token_urlsafe(12)
    
    def _create_context_snapshot(self, session_id: str, research_data: Dict) -> ContextSnapshot:
        """Create a snapshot of current research context"""
        
        # Extract key context elements
        query = research_data.get("query", "")
        findings = research_data.get("findings", [])
        sources = research_data.get("sources", [])
        confidence_scores = research_data.get("confidence_scores", {})
        
        # Extract agent states and reasoning chains
        agent_states = {}
        reasoning_chains = {}
        
        for agent_id, agent_data in research_data.get("agents", {}).items():
            agent_states[agent_id] = {
                "status": agent_data.get("status", "unknown"),
                "progress": agent_data.get("progress", 0),
                "current_task": agent_data.get("current_task", ""),
                "output_preview": agent_data.get("output", "")[:200]
            }
            
            # Extract reasoning chain if available
            reasoning = agent_data.get("reasoning_chain", [])
            if reasoning:
                reasoning_chains[agent_id] = reasoning
        
        # Create metadata
        metadata = {
            "pipeline_version": research_data.get("pipeline_version", "1.0"),
            "model_provider": research_data.get("model_provider", "unknown"),
            "quality_metrics": research_data.get("quality_metrics", {}),
            "session_duration": research_data.get("session_duration", 0),
            "total_tokens": research_data.get("total_tokens", 0)
        }
        
        return ContextSnapshot(
            snapshot_id=f"snap_{secrets.token_hex(8)}",
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            query=query,
            agent_states=agent_states,
            findings=findings,
            sources=sources,
            confidence_scores=confidence_scores,
            reasoning_chains=reasoning_chains,
            metadata=metadata
        )
    
    def create_collaboration_session(self,
                                 original_session_id: str,
                                 owner_id: str,
                                 title: str,
                                 description: str,
                                 research_data: Dict,
                                 permission_level: PermissionLevel = PermissionLevel.READ_ONLY,
                                 expires_hours: int = 168) -> Dict:  # 1 week default
        """Create a new collaboration session"""
        
        # Generate session ID and access code
        session_id = f"collab_{secrets.token_hex(8)}"
        access_code = self._generate_access_code()
        
        # Create collaboration session
        session = CollaborationSession(
            session_id=session_id,
            original_session_id=original_session_id,
            owner_id=owner_id,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=expires_hours)).isoformat(),
            permission_level=permission_level,
            research_data=research_data,
            comments=[],
            contributors=[owner_id],
            is_active=True
        )
        
        # Store session and access code
        self.collaboration_sessions[session_id] = session
        self.access_codes[access_code] = session_id
        
        # Create context snapshot
        snapshot = self._create_context_snapshot(original_session_id, research_data)
        self.context_snapshots[snapshot.snapshot_id] = snapshot
        
        self._save_data()
        
        return {
            "session_id": session_id,
            "access_code": access_code,
            "snapshot_id": snapshot.snapshot_id,
            "expires_at": session.expires_at,
            "share_url": f"/collaborate/{access_code}",
            "permission_level": permission_level.value
        }
    
    def access_collaboration_session(self, access_code: str, user_id: str) -> Dict:
        """Access a collaboration session via access code"""
        
        session_id = self.access_codes.get(access_code)
        if not session_id:
            return {"error": "Invalid access code"}
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check if session is expired
        if datetime.now() > datetime.fromisoformat(session.expires_at):
            return {"error": "Session has expired"}
        
        # Check if session is active
        if not session.is_active:
            return {"error": "Session is not active"}
        
        # Add user to contributors if not already present
        if user_id not in session.contributors:
            session.contributors.append(user_id)
            self._save_data()
        
        # Get context snapshot
        snapshot = self.context_snapshots.get(
            next(iter(self.context_snapshots.keys()))  # Get first snapshot for this session
        )
        
        return {
            "session": {
                "session_id": session.session_id,
                "title": session.title,
                "description": session.description,
                "permission_level": session.permission_level.value,
                "owner_id": session.owner_id,
                "contributors": session.contributors,
                "created_at": session.created_at,
                "expires_at": session.expires_at
            },
            "context_snapshot": {
                "snapshot_id": snapshot.snapshot_id if snapshot else None,
                "query": snapshot.query if snapshot else "",
                "findings": snapshot.findings if snapshot else [],
                "sources": snapshot.sources if snapshot else [],
                "confidence_scores": snapshot.confidence_scores if snapshot else {},
                "agent_states": snapshot.agent_states if snapshot else {},
                "reasoning_chains": snapshot.reasoning_chains if snapshot else {},
                "metadata": snapshot.metadata if snapshot else {}
            },
            "research_data": session.research_data,
            "comments": session.comments
        }
    
    def add_comment(self, session_id: str, user_id: str, comment: str, 
                   target_section: str = None, target_claim: str = None) -> Dict:
        """Add a comment to collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check permissions
        if session.permission_level == PermissionLevel.READ_ONLY:
            return {"error": "No permission to comment"}
        
        # Create comment
        comment_data = {
            "comment_id": f"comment_{secrets.token_hex(6)}",
            "user_id": user_id,
            "comment": comment,
            "target_section": target_section,
            "target_claim": target_claim,
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        }
        
        session.comments.append(comment_data)
        self._save_data()
        
        return {"comment_added": True, "comment_id": comment_data["comment_id"]}
    
    def resolve_comment(self, session_id: str, comment_id: str, user_id: str) -> Dict:
        """Resolve a comment"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check permissions (only owner or comment author can resolve)
        comment = next((c for c in session.comments if c["comment_id"] == comment_id), None)
        if not comment:
            return {"error": "Comment not found"}
        
        if user_id not in [session.owner_id, comment["user_id"]]:
            return {"error": "No permission to resolve comment"}
        
        comment["resolved"] = True
        comment["resolved_by"] = user_id
        comment["resolved_at"] = datetime.now().isoformat()
        
        self._save_data()
        
        return {"comment_resolved": True}
    
    def create_context_handoff(self, session_id: str, research_data: Dict, 
                              target_user: str = None, message: str = "") -> Dict:
        """Create a context handoff for another researcher"""
        
        # Create context snapshot
        snapshot = self._create_context_snapshot(session_id, research_data)
        self.context_snapshots[snapshot.snapshot_id] = snapshot
        
        # Create handoff collaboration session
        handoff_session = self.create_collaboration_session(
            original_session_id=session_id,
            owner_id="system",  # System handoff
            title=f"Context Handoff: {research_data.get('query', 'Research Session')}",
            description=message or "Research context handed off for continuation",
            research_data=research_data,
            permission_level=PermissionLevel.EDIT,
            expires_hours=72  # 3 days for handoffs
        )
        
        return {
            "handoff_created": True,
            "snapshot_id": snapshot.snapshot_id,
            "collaboration_session": handoff_session,
            "target_user": target_user,
            "handoff_message": message
        }
    
    def get_user_sessions(self, user_id: str) -> Dict:
        """Get all collaboration sessions for a user"""
        
        user_sessions = []
        for session in self.collaboration_sessions.values():
            if user_id in session.contributors:
                user_sessions.append({
                    "session_id": session.session_id,
                    "title": session.title,
                    "description": session.description,
                    "permission_level": session.permission_level.value,
                    "is_owner": session.owner_id == user_id,
                    "created_at": session.created_at,
                    "expires_at": session.expires_at,
                    "is_active": session.is_active,
                    "contributor_count": len(session.contributors),
                    "comment_count": len(session.comments)
                })
        
        # Sort by creation date (newest first)
        user_sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "user_id": user_id,
            "sessions": user_sessions,
            "total_sessions": len(user_sessions)
        }
    
    def revoke_access(self, session_id: str, user_id: str) -> Dict:
        """Revoke access to a collaboration session"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Only owner can revoke access
        if session.owner_id != user_id:
            return {"error": "Only owner can revoke access"}
        
        # Deactivate session
        session.is_active = False
        
        # Remove access codes
        codes_to_remove = [code for code, sid in self.access_codes.items() if sid == session_id]
        for code in codes_to_remove:
            del self.access_codes[code]
        
        self._save_data()
        
        return {"access_revoked": True, "session_id": session_id}
    
    def extend_session(self, session_id: str, user_id: str, hours: int = 168) -> Dict:
        """Extend collaboration session expiration"""
        
        session = self.collaboration_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Only owner can extend
        if session.owner_id != user_id:
            return {"error": "Only owner can extend session"}
        
        # Extend expiration
        current_expiry = datetime.fromisoformat(session.expires_at)
        new_expiry = current_expiry + timedelta(hours=hours)
        session.expires_at = new_expiry.isoformat()
        
        self._save_data()
        
        return {
            "session_extended": True,
            "new_expires_at": session.expires_at,
            "hours_extended": hours
        }


# Global collaboration manager
collaboration_manager = CollaborationManager()


def create_collaboration_session(original_session_id: str, owner_id: str, title: str, 
                             description: str, research_data: Dict, 
                             permission_level: str = "read_only") -> Dict:
    """Public interface for creating collaboration sessions"""
    perm_level = PermissionLevel(permission_level)
    return collaboration_manager.create_collaboration_session(
        original_session_id, owner_id, title, description, research_data, perm_level
    )


def access_collaboration_session(access_code: str, user_id: str) -> Dict:
    """Public interface for accessing collaboration sessions"""
    return collaboration_manager.access_collaboration_session(access_code, user_id)


def create_context_handoff(session_id: str, research_data: Dict, 
                         target_user: str = None, message: str = "") -> Dict:
    """Public interface for creating context handoffs"""
    return collaboration_manager.create_context_handoff(
        session_id, research_data, target_user, message
    )

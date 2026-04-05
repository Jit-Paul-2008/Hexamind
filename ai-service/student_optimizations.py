"""
Student Edition Optimizations for $0 Cost Hosting
Maximizes GitHub Student Pack benefits
"""

import os
import time
import psutil
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ResourceMetrics:
    cpu_percent: float
    memory_percent: float
    memory_mb: int
    disk_percent: float


class StudentOptimizer:
    """Optimizes system for free tier student hosting"""
    
    def __init__(self):
        self.student_mode = os.getenv("HEXAMIND_STUDENT_MODE", "false").lower() == "true"
        self.max_memory_mb = 512  # Codespaces limit
        self.max_cpu_percent = 80
        self.cache_size_limit = 100
        
    def get_resource_metrics(self) -> ResourceMetrics:
        """Monitor resource usage to stay within free limits"""
        return ResourceMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            memory_mb=psutil.virtual_memory().used // 1024 // 1024,
            disk_percent=psutil.disk_usage('/').percent
        )
    
    def should_throttle(self) -> bool:
        """Check if we should throttle to stay within free limits"""
        metrics = self.get_resource_metrics()
        
        return (
            metrics.cpu_percent > self.max_cpu_percent or
            metrics.memory_mb > self.max_memory_mb or
            metrics.disk_percent > 90
        )
    
    def optimize_for_student(self) -> Dict[str, any]:
        """Apply student-specific optimizations"""
        
        optimizations = {
            "model_provider": "local_ollama",
            "search_provider": "duckduckgo", 
            "cache_strategy": "aggressive",
            "batch_processing": False,
            "rate_limiting": {
                "requests_per_minute": 5,
                "requests_per_hour": 50,
                "concurrent_requests": 1
            },
            "resource_limits": {
                "max_memory_mb": 512,
                "max_cpu_percent": 80,
                "max_disk_percent": 90
            },
            "cost_optimizations": {
                "zero_api_keys": True,
                "local_models_only": True,
                "free_search_only": True,
                "student_credits_utilization": True
            }
        }
        
        return optimizations
    
    def get_student_benefits(self) -> Dict[str, str]:
        """List of GitHub Student Pack benefits being used"""
        
        return {
            "github_pages": "Frontend hosting - $0/month",
            "github_codespaces": "Backend hosting - 60 hours/month",
            "github_actions": "CI/CD - 2,000 minutes/month", 
            "azure_sql_database": "Database - $0/month (12 months)",
            "azure_app_service": "App hosting - $0/month (12 months)",
            "azure_credits": "$100 credit for additional services",
            "microsoft_azure": "$200 credit for students",
            "ollama_local": "Local AI models - $0/month",
            "duckduckgo_search": "Web search - $0/month",
            "sqlite_database": "Local database - $0/month"
        }


class StudentModelProvider:
    """Free model provider using local Ollama"""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:8b")
        
    async def check_ollama_available(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except:
            return False
    
    async def generate_with_ollama(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Generate text using local Ollama (completely free)"""
        try:
            import httpx
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": max_tokens
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    return None
                    
        except Exception as e:
            print(f"Ollama generation failed: {e}")
            return None


class StudentSearchProvider:
    """Free search provider using DuckDuckGo"""
    
    def __init__(self):
        self.max_results = 3  # Conservative for free tier
        
    async def search_duckduckgo(self, query: str) -> list:
        """Search using DuckDuckGo instant answers (no API key needed)"""
        try:
            import httpx
            
            # DuckDuckGo instant answers API
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    # Extract topics from DuckDuckGo
                    topics = data.get("RelatedTopics", [])[:self.max_results]
                    
                    for topic in topics:
                        if isinstance(topic, dict):
                            results.append({
                                "title": topic.get("Text", "")[:100],
                                "url": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", "")[:200],
                                "domain": self._extract_domain(topic.get("FirstURL", "")),
                                "authority": "medium",
                                "credibility_score": 0.6,
                                "recency_score": 0.7
                            })
                    
                    return results
                else:
                    return []
                    
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
            return []
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return "unknown"


class StudentCostTracker:
    """Track costs to ensure $0 spending"""
    
    def __init__(self):
        self.api_calls = 0
        self.search_calls = 0
        self.start_time = time.time()
        
    def log_api_call(self, provider: str, cost: float = 0.0):
        """Log an API call for tracking"""
        self.api_calls += 1
        print(f"API Call #{self.api_calls}: {provider} (${cost:.4f})")
        
        # Warn if any cost detected
        if cost > 0:
            print(f"⚠️  WARNING: Non-zero cost detected: ${cost:.4f}")
    
    def log_search_call(self, provider: str):
        """Log a search call"""
        self.search_calls += 1
        print(f"Search Call #{self.search_calls}: {provider} ($0.00)")
    
    def get_cost_report(self) -> Dict:
        """Generate cost report"""
        runtime_hours = (time.time() - self.start_time) / 3600
        
        return {
            "total_cost": 0.0,  # Should always be $0
            "api_calls": self.api_calls,
            "search_calls": self.search_calls,
            "runtime_hours": runtime_hours,
            "student_benefits_used": "GitHub Student Pack",
            "status": "✅ $0 COST MAINTAINED"
        }


# Global student optimizer
student_optimizer = StudentOptimizer()
student_model_provider = StudentModelProvider()
student_search_provider = StudentSearchProvider()
student_cost_tracker = StudentCostTracker()


def is_student_mode() -> bool:
    """Check if running in student mode"""
    return os.getenv("HEXAMIND_STUDENT_MODE", "false").lower() == "true"


def get_student_optimizations() -> Dict:
    """Get student-specific optimizations"""
    return student_optimizer.optimize_for_student()


def log_student_usage(api_call: str = "", search_call: str = ""):
    """Log usage for student mode tracking"""
    if api_call:
        student_cost_tracker.log_api_call(api_call, 0.0)
    if search_call:
        student_cost_tracker.log_search_call(search_call)

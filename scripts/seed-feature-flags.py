"""
Feature Flag Seeding Script
Initializes all feature flags in the configured provider
Run: python scripts/seed-feature-flags.py
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List

class FeatureFlagManager:
    """Manages feature flags across different providers"""
    
    # Define all feature flags with defaults and metadata
    FEATURE_FLAGS = {
        "enable_new_ui": {
            "description": "Enable new ARIA Claude-like UI",
            "default": False,
            "rollout_percentage": 0,
            "tier": "beta",
            "owner": "engineering",
            "labels": ["ui", "critical"],
        },
        "enable_database_persistence": {
            "description": "Enable database-backed storage instead of in-memory",
            "default": False,
            "rollout_percentage": 0,
            "tier": "beta",
            "owner": "backend",
            "labels": ["database", "critical"],
        },
        "enable_advanced_compare": {
            "description": "Enable advanced run comparison features",
            "default": False,
            "rollout_percentage": 50,
            "tier": "alpha",
            "owner": "product",
            "labels": ["ui", "comparison"],
        },
        "enable_sharing": {
            "description": "Enable case sharing and public links",
            "default": True,
            "rollout_percentage": 100,
            "tier": "production",
            "owner": "product",
            "labels": ["collaboration", "sharing"],
        },
        "enable_audit_logs": {
            "description": "Enable comprehensive audit logging",
            "default": True,
            "rollout_percentage": 100,
            "tier": "production",
            "owner": "security",
            "labels": ["security", "compliance"],
        },
        "enable_sse_reconnect": {
            "description": "Enable automatic SSE reconnection on disconnect",
            "default": True,
            "rollout_percentage": 100,
            "tier": "production",
            "owner": "backend",
            "labels": ["reliability", "streaming"],
        },
        "enable_cost_tracking": {
            "description": "Enable cost tracking per run",
            "default": True,
            "rollout_percentage": 100,
            "tier": "production",
            "owner": "product",
            "labels": ["billing", "analytics"],
        },
        "enable_org_management": {
            "description": "Enable organization and team member management",
            "default": False,
            "rollout_percentage": 25,
            "tier": "beta",
            "owner": "product",
            "labels": ["collaboration", "org"],
        },
        "enable_sso_google": {
            "description": "Enable Google SSO authentication",
            "default": False,
            "rollout_percentage": 50,
            "tier": "alpha",
            "owner": "auth",
            "labels": ["authentication", "sso"],
        },
        "enable_sso_github": {
            "description": "Enable GitHub SSO authentication",
            "default": False,
            "rollout_percentage": 50,
            "tier": "alpha",
            "owner": "auth",
            "labels": ["authentication", "sso"],
        },
        "enable_batch_operations": {
            "description": "Enable bulk case/run operations",
            "default": False,
            "rollout_percentage": 10,
            "tier": "alpha",
            "owner": "product",
            "labels": ["ux", "batch"],
        },
        "enable_scenario_testing": {
            "description": "Enable scenario testing mode",
            "default": False,
            "rollout_percentage": 25,
            "tier": "beta",
            "owner": "product",
            "labels": ["testing", "research"],
        },
        "enable_api_v2": {
            "description": "Enable new v2 API endpoints",
            "default": True,
            "rollout_percentage": 100,
            "tier": "production",
            "owner": "backend",
            "labels": ["api", "critical"],
        },
        "enable_webhooks": {
            "description": "Enable webhook triggers for run completion",
            "default": False,
            "rollout_percentage": 0,
            "tier": "alpha",
            "owner": "integrations",
            "labels": ["integrations", "webhooks"],
        },
        "enable_caching": {
            "description": "Enable Redis caching layer",
            "default": False,
            "rollout_percentage": 50,
            "tier": "beta",
            "owner": "infrastructure",
            "labels": ["performance", "caching"],
        },
    }

    def __init__(self):
        self.provider = os.getenv("FEATURE_FLAG_PROVIDER", "memory").lower()
        self.flags_data = {}

    async def initialize(self):
        """Initialize flags in the configured provider"""
        print(f"🚀 Initializing feature flags with provider: {self.provider}")
        
        if self.provider == "memory":
            await self._init_memory()
        elif self.provider == "redis":
            await self._init_redis()
        elif self.provider == "launchdarkly":
            await self._init_launchdarkly()
        elif self.provider == "unleash":
            await self._init_unleash()
        else:
            print(f"❌ Unknown provider: {self.provider}")
            return False
        
        return True

    async def _init_memory(self):
        """Initialize in-memory flags (from environment)"""
        print("  → Using in-memory feature flag provider (environment variables)")
        
        for flag_key, flag_config in self.FEATURE_FLAGS.items():
            env_key = f"FLAG_{flag_key.upper()}"
            default_value = flag_config["default"]
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                value = env_value.lower() in ("true", "1", "yes", "on")
            else:
                value = default_value
            
            self.flags_data[flag_key] = {
                **flag_config,
                "value": value,
                "env_key": env_key,
            }
            
            status = "✓" if value else "✗"
            print(f"    {status} {flag_key}: {value}")

    async def _init_redis(self):
        """Initialize in Redis (if available)"""
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        
        try:
            r = await redis.from_url(redis_url)
            print(f"  → Connected to Redis: {redis_url}")
            
            for flag_key, flag_config in self.FEATURE_FLAGS.items():
                value = flag_config["default"]
                await r.hset(
                    f"feature_flags:{flag_key}",
                    mapping={
                        "enabled": str(value).lower(),
                        "description": flag_config["description"],
                        "owner": flag_config["owner"],
                        "tier": flag_config["tier"],
                        "rollout_percentage": str(flag_config["rollout_percentage"]),
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
                status = "✓" if value else "✗"
                print(f"    {status} {flag_key}: {value}")
            
            await r.close()
        except Exception as e:
            print(f"  ❌ Redis Connection Failed: {e}")

    async def _init_launchdarkly(self):
        """Initialize in LaunchDarkly"""
        sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY")
        
        if not sdk_key:
            print("  ❌ LaunchDarkly SDK key not provided")
            return
        
        try:
            import ldclient
            from ldclient.config import Config
            
            ldclient.set_config(Config(sdk_key))
            client = ldclient.get()
            
            print(f"  → Connected to LaunchDarkly")
            
            # Note: LaunchDarkly SDK doesn't have direct flag creation
            # Flags should be created in the LaunchDarkly dashboard
            # This script just warns the user
            
            for flag_key in self.FEATURE_FLAGS.keys():
                print(f"    ⚠️  {flag_key} (must be created in LaunchDarkly dashboard)")
            
            print("\n  📋 Please create these flags in LaunchDarkly:")
            for flag_key, config in self.FEATURE_FLAGS.items():
                print(f"     - {flag_key}: ({config['tier']}) {config['description']}")
        
        except Exception as e:
            print(f"  ❌ LaunchDarkly Error: {e}")

    async def _init_unleash(self):
        """Initialize in Unleash"""
        api_token = os.getenv("UNLEASH_API_TOKEN")
        api_url = os.getenv("UNLEASH_API_URL", "http://localhost:4242")
        
        if not api_token:
            print("  ❌ Unleash API token not provided")
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient(
                base_url=api_url,
                headers={"Authorization": api_token},
                timeout=10,
            ) as client:
                print(f"  → Connected to Unleash: {api_url}")
                
                for flag_key, flag_config in self.FEATURE_FLAGS.items():
                    feature_def = {
                        "name": flag_key,
                        "description": flag_config["description"],
                        "type": "release",
                        "enabled": flag_config["default"],
                        "strategies": [
                            {
                                "name": "default",
                                "parameters": {
                                    "rollout": str(flag_config["rollout_percentage"]),
                                }
                            }
                        ],
                        "tags": flag_config["labels"],
                    }
                    
                    try:
                        response = await client.post(
                            "/api/admin/features",
                            json=feature_def,
                        )
                        
                        if response.status_code in (201, 409):  # 409 = already exists
                            status = "✓" if flag_config["default"] else "✗"
                            print(f"    {status} {flag_key}")
                        else:
                            print(f"    ❌ {flag_key}: {response.status_code}")
                    
                    except Exception as e:
                        print(f"    ❌ {flag_key}: {e}")
        
        except Exception as e:
            print(f"  ❌ Unleash Connection Error: {e}")

    async def export_config(self):
        """Export current flag configuration to JSON"""
        export_path = "feature-flags-config.json"
        
        config = {
            "exported_at": datetime.utcnow().isoformat(),
            "provider": self.provider,
            "flags": self.flags_data or self.FEATURE_FLAGS,
        }
        
        with open(export_path, "w") as f:
            json.dump(config, f, indent=2, default=str)
        
        print(f"\n📄 Configuration exported to: {export_path}")

    async def print_summary(self):
        """Print summary of all flags"""
        print("\n" + "="*70)
        print("FEATURE FLAG SUMMARY")
        print("="*70)
        
        flags_by_tier = {}
        for flag_key, config in self.FEATURE_FLAGS.items():
            tier = config["tier"]
            if tier not in flags_by_tier:
                flags_by_tier[tier] = []
            
            enabled = self.flags_data.get(flag_key, {}).get("value", config["default"])
            flags_by_tier[tier].append((flag_key, config, enabled))
        
        for tier in ["production", "beta", "alpha"]:
            if tier in flags_by_tier:
                print(f"\n{tier.upper()}:")
                for flag_key, config, enabled in flags_by_tier[tier]:
                    status = "✓ ENABLED " if enabled else "✗ DISABLED"
                    rollout = f"({config['rollout_percentage']}%)" if config['rollout_percentage'] < 100 else ""
                    print(f"  {status} {flag_key} {rollout}")
                    print(f"      {config['description']}")
                    print(f"      Owner: {config['owner']}")
        
        print("\n" + "="*70)


async def main():
    """Main execution"""
    manager = FeatureFlagManager()
    
    success = await manager.initialize()
    
    if success:
        await manager.print_summary()
        await manager.export_config()
        print("\n✅ Feature flags initialized successfully")
    else:
        print("\n❌ Feature flag initialization failed")


if __name__ == "__main__":
    asyncio.run(main())

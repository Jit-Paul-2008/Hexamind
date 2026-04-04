#!/usr/bin/env python3
"""
Load Testing Harness for ARIA UX
Simulates realistic user traffic patterns
Run: python scripts/load-test.py --users 100 --duration 600
"""

import asyncio
import json
import time
import statistics
from dataclasses import dataclass
from typing import List
import argparse
import aiohttp
from datetime import datetime

@dataclass
class RequestMetrics:
    """Track individual request performance"""
    method: str
    endpoint: str
    status_code: int
    response_time_ms: float
    timestamp: float
    error: str | None = None


class LoadTester:
    def __init__(self, base_url: str, num_users: int, duration_seconds: int):
        self.base_url = base_url
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.metrics: List[RequestMetrics] = []
        self.session = None
        self.start_time = None
        self.auth_tokens = {}

    async def setup(self):
        """Initialize session and get auth tokens"""
        connector = aiohttp.TCPConnector(limit=self.num_users * 2)
        self.session = aiohttp.ClientSession(connector=connector)
        self.start_time = time.time()

        # Pre-authenticate users
        tasks = []
        for i in range(self.num_users):
            user_email = f"loadtest{i}@example.com"
            tasks.append(self._register_and_login(user_email, f"password{i}"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, str):
                self.auth_tokens[f"loadtest{i}@example.com"] = result
            else:
                print(f"⚠️  User {i} auth failed: {result}")

        print(f"✓ Authenticated {len(self.auth_tokens)} users")

    async def _register_and_login(self, email: str, password: str) -> str | None:
        """Register user and return auth token"""
        try:
            # Register
            async with self.session.post(
                f"{self.base_url}/api/auth/register",
                json={"email": email, "password": password}
            ) as resp:
                if resp.status not in [200, 201, 409]:  # 409 = user exists
                    return None

            # Login
            async with self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": email, "password": password}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("access_token")
                return None
        except Exception as e:
            print(f"Auth error for {email}: {e}")
            return None

    async def _make_request(
        self,
        user_index: int,
        method: str,
        endpoint: str,
        json_body: dict | None = None,
    ) -> RequestMetrics:
        """Make single request and collect metrics"""
        user_email = f"loadtest{user_index}@example.com"
        token = self.auth_tokens.get(user_email)
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        start = time.time()
        try:
            async with self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                json=json_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                response_time_ms = (time.time() - start) * 1000
                status_code = resp.status
                _ = await resp.text()  # Consume response body

                return RequestMetrics(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    timestamp=time.time(),
                )
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start) * 1000
            return RequestMetrics(
                method=method,
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                timestamp=time.time(),
                error="Timeout",
            )
        except Exception as e:
            response_time_ms = (time.time() - start) * 1000
            return RequestMetrics(
                method=method,
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time_ms,
                timestamp=time.time(),
                error=str(e),
            )

    async def simulate_user_workflow(self, user_index: int):
        """Simulate realistic user behavior"""
        user_email = f"loadtest{user_index}@example.com"
        
        while time.time() - self.start_time < self.duration_seconds:
            # Workflow: List projects → Create case → Run ARIA → Get quality
            
            # GET /api/v2/organizations
            metrics = await self._make_request(user_index, "GET", "/api/v2/organizations")
            self.metrics.append(metrics)
            
            if metrics.status_code == 200:
                await asyncio.sleep(0.2)  # Think time
                
                # POST /api/v2/projects (create project)
                project_payload = {
                    "name": f"LoadTest Project {int(time.time())}",
                    "description": f"User {user_index} project",
                }
                metrics = await self._make_request(
                    user_index, "POST", "/api/v2/projects", project_payload
                )
                self.metrics.append(metrics)
                
                await asyncio.sleep(0.2)
                
                # GET /api/v2/projects
                metrics = await self._make_request(user_index, "GET", "/api/v2/projects")
                self.metrics.append(metrics)
                
                if metrics.status_code == 200:
                    await asyncio.sleep(0.2)
                    
                    # POST /api/v2/cases (create case)
                    case_payload = {
                        "name": f"LoadTest Case {int(time.time())}",
                        "initial_question": f"What is AI? (User {user_index})",
                        "project_id": f"mock-project-{user_index}",
                    }
                    metrics = await self._make_request(
                        user_index, "POST", "/api/v2/cases", case_payload
                    )
                    self.metrics.append(metrics)
                    
                    await asyncio.sleep(0.5)
                    
                    # GET /api/v2/cases
                    metrics = await self._make_request(user_index, "GET", "/api/v2/cases")
                    self.metrics.append(metrics)
                    
                    # POST /api/pipeline/start (start ARIA)
                    pipeline_payload = {
                        "question": "What is AI?",
                        "mode": "deep_research",
                    }
                    metrics = await self._make_request(
                        user_index,
                        "POST",
                        "/api/pipeline/start",
                        pipeline_payload,
                    )
                    self.metrics.append(metrics)
                    
                    await asyncio.sleep(1)  # Longer think time after running ARIA
                    
                    # GET /api/models/status
                    metrics = await self._make_request(user_index, "GET", "/api/models/status")
                    self.metrics.append(metrics)
            
            await asyncio.sleep(5)  # 5-second delay between workflows

    async def run(self):
        """Execute load test"""
        await self.setup()
        print(f"\n🚀 Starting load test: {self.num_users} users, {self.duration_seconds}s duration")
        print(f"   Start time: {datetime.now().isoformat()}")
        
        # Create tasks for all users
        tasks = [
            self.simulate_user_workflow(i)
            for i in range(self.num_users)
        ]
        
        # Run all concurrently
        await asyncio.gather(*tasks)
        
        # Close session
        await self.session.close()

    def report(self):
        """Generate performance report"""
        if not self.metrics:
            print("❌ No metrics collected")
            return

        # Filter out errors for response time calculations
        successful = [m for m in self.metrics if m.error is None]
        failed = [m for m in self.metrics if m.error is not None]
        
        response_times = [m.response_time_ms for m in successful]
        
        if not response_times:
            print("❌ No successful requests")
            return

        # Calculate percentiles
        response_times_sorted = sorted(response_times)
        p50 = statistics.median(response_times_sorted)
        p95 = response_times_sorted[int(len(response_times_sorted) * 0.95)]
        p99 = response_times_sorted[int(len(response_times_sorted) * 0.99)]
        
        # Print report
        print("\n" + "="*70)
        print("LOAD TEST REPORT")
        print("="*70)
        print(f"Duration:              {self.duration_seconds}s")
        print(f"Concurrent Users:      {self.num_users}")
        print(f"Total Requests:        {len(self.metrics)}")
        print(f"Successful:            {len(successful)}")
        print(f"Failed:                {len(failed)}")
        print(f"Success Rate:          {len(successful) / len(self.metrics) * 100:.1f}%")
        print(f"\nResponse Time (ms):")
        print(f"  Min:                 {min(response_times):.2f}")
        print(f"  Max:                 {max(response_times):.2f}")
        print(f"  Mean:                {statistics.mean(response_times):.2f}")
        print(f"  Median (P50):        {p50:.2f}")
        print(f"  P95:                 {p95:.2f}")
        print(f"  P99:                 {p99:.2f}")
        print(f"  StdDev:              {statistics.stdev(response_times):.2f}")
        print(f"\nThroughput:            {len(successful) / self.duration_seconds:.1f} req/s")
        
        # Status code breakdown
        status_codes = {}
        for m in self.metrics:
            status = m.status_code or "TIMEOUT"
            status_codes[status] = status_codes.get(status, 0) + 1
        
        print(f"\nStatus Codes:")
        for status, count in sorted(status_codes.items()):
            print(f"  {status}: {count}")
        
        if failed:
            print(f"\nErrors:")
            error_types = {}
            for m in failed:
                error_types[m.error] = error_types.get(m.error, 0) + 1
            for error, count in sorted(error_types.items()):
                print(f"  {error}: {count}")
        
        # Endpoint breakdown
        print(f"\nEndpoint Performance:")
        endpoints = {}
        for m in self.metrics:
            key = f"{m.method} {m.endpoint}"
            if key not in endpoints:
                endpoints[key] = []
            endpoints[key].append(m.response_time_ms)
        
        for endpoint in sorted(endpoints.keys()):
            times = endpoints[endpoint]
            print(f"  {endpoint}")
            print(f"    Calls:  {len(times)}")
            print(f"    Mean:   {statistics.mean(times):.2f}ms")
            print(f"    P95:    {sorted(times)[int(len(times)*0.95)]:.2f}ms")
        
        # Save detailed metrics to JSON
        metrics_file = f"load-test-results-{int(time.time())}.json"
        with open(metrics_file, "w") as f:
            json.dump(
                [
                    {
                        "method": m.method,
                        "endpoint": m.endpoint,
                        "status_code": m.status_code,
                        "response_time_ms": m.response_time_ms,
                        "timestamp": m.timestamp,
                        "error": m.error,
                    }
                    for m in self.metrics
                ],
                f,
                indent=2,
            )
        print(f"\n📊 Detailed metrics saved to: {metrics_file}")
        print("="*70 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="Load test ARIA UX")
    parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Base URL of the application",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the API",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of concurrent users",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration of test in seconds",
    )
    
    args = parser.parse_args()
    
    # Override base_url with api_url for API calls
    tester = LoadTester(args.api_url, args.users, args.duration)
    await tester.run()
    tester.report()


if __name__ == "__main__":
    asyncio.run(main())

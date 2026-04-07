import json
import os
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
from inference_provider import InferenceProvider

logger = logging.getLogger(__name__)

SIMULATION_PROMPT = """You are the Hexamind Quantitative Simulation Engine.
The user wants to run a mathematical model or comparative simulation.
Your job is to WRITE PURE PYTHON CODE that uses pandas, numpy, and scipy to calculate the results and print a specific JSON object.

The parameters:
{scenario}

Rules for your Python code:
1. Use `import json`, `import numpy as np`, `import pandas as pd`, `from scipy import stats` etc.
2. Calculate the historical trends, comparative ROI, or projections as requested, mapping different scenarios if comparisons are requested.
3. You must construct a JSON ARRAY (a python list of dictionaries) with the exact following schema:
[
  {{
    "chartType": "area", // or "bar" or "line" or "radar"
    "title": "Descriptive Chart Title (e.g., Scenario A)",
    "xAxis": "Label for X",
    "yAxis": "Label for Y",
    "data": [
        {{"Year": "2024", "Metric A": 100, "Metric B": 200}},
        {{"Year": "2025", "Metric A": 150, "Metric B": 180}}
    ]
  }},
  {{
     "chartType": "bar",
     "title": "Scenario B",
     "xAxis": "...",
     "yAxis": "...",
     "data": [...]
  }}
]
4. Use `print(json.dumps(final_list))` at the very end of your script to output the data.
5. DO NOT print anything else. DO NOT use markdown code blocks like ```python. Just output raw valid Python code.
"""

class SimulationWorker:
    def __init__(self, provider: InferenceProvider):
        self.provider = provider
        
    async def simulate(self, scenario: str, context: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Generates dynamic python code, executes it, and retrieves the JSON chart data."""
        prompt = SIMULATION_PROMPT.format(scenario=scenario)
        
        # Add context from research if applicable
        ctx_text = ""
        if context:
            ctx_text = "\n\nBACKGROUND CONTEXT TO USE IN DATA ARRAYS:\n"
            for c in context:
                if 'content' in c:
                    ctx_text += c['content'][:1000] + "\n"
        prompt += ctx_text
        
        logger.info("Generating Simulation Script via LLM...")
        script_code = await self.provider.generate(prompt)
        
        # Clean up possible markdown
        script_code = script_code.strip()
        if script_code.startswith("```python"):
            script_code = script_code[9:]
        if script_code.startswith("```"):
            script_code = script_code[3:]
        if script_code.endswith("```"):
            script_code = script_code[:-3]
        script_code = script_code.strip()
        
        logger.info(f"Executing mathematical model length: {len(script_code)} chars")
        
        # Sandbox execution
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
            temp_script.write(script_code)
            temp_path = temp_script.name
            
        try:
            # We enforce a timeout so it doesn't hang forever
            result = subprocess.run(
                ["python3", temp_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                logger.error(f"Simulation script failed: {result.stderr}")
                return None
                
            stdout_output = result.stdout.strip()
            
            # Find the JSON part
            try:
                # the simplest way is to parse the last valid json blob (now an array)
                json_start = stdout_output.find("[")
                json_end = stdout_output.rfind("]") + 1
                if json_start != -1 and json_end != -1:
                    json_str = stdout_output[json_start:json_end]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list) and len(parsed) > 0 and "data" in parsed[0]:
                        return parsed
            except Exception as parse_e:
                logger.error(f"Failed to parse mathematical output: {parse_e}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Simulation script timed out")
            return None
        except Exception as e:
            logger.error(f"Simulation execution error: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return None

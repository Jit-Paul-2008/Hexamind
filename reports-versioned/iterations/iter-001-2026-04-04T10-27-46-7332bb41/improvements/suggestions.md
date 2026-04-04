[
  {
    "title": "Broaden source coverage",
    "description": "Add more diverse local sources and enable live web research for corroboration.",
    "config_changes": {
      "AUTONOMOUS_MIN_SOURCE_COVERAGE": "0.9",
      "AUTONOMOUS_MIN_SOURCE_COUNT": "4",
      "AUTONOMOUS_MIN_SOURCE_DIVERSITY": "3",
      "HEXAMIND_WEB_RESEARCH": "1"
    },
    "expected_impact": 0.35,
    "confidence": 0.9
  },
  {
    "title": "Strengthen extraction depth",
    "description": "Increase extracted character budget and require richer source corpora before research starts.",
    "config_changes": {
      "AUTONOMOUS_MIN_EXTRACTED_CHARS": "142472",
      "AUTONOMOUS_IMPROVEMENT_MIN_DELTA": "0.08"
    },
    "expected_impact": 0.28,
    "confidence": 0.85
  }
]
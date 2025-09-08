# json_schema.py
FINAL_STRATEGY_SCHEMA = {
    "type": "object",
    "required": ["executive_summary", "key_findings", "strategic_recommendations"],
    "properties": {
        "executive_summary": {"type": "string"},
        "key_findings": {"type": "object"},
        "conflicts": {"type": "array"},
        "strategic_recommendations": {"type": "array"}
    }
}

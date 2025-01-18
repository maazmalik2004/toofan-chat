data = {
    "knowledge_summaries": [
        {
            "artifact_id": "235568a6-32ef-47f7-8d14-a2573d34133b",
            "artifact_summary": "The provided texts consistently highlight several overarching themes..."
        },
        {
            "artifact_id": "235568a6-32ef-47f7-8d14-a2573d34133b",
            "artifact_summary": "Another summary for the same artifact_id"
        },
        {
            "artifact_id": "random-id-1234",
            "artifact_summary": "This record should remain unaffected."
        }
    ]
}

artifact_ids_to_remove = {"235568a6-32ef-47f7-8d14-a2573d34133b", "another-id-1234"}

# Iteratively remove records with any artifact_id in the removal set
data["knowledge_summaries"] = [record for record in data["knowledge_summaries"] if record["artifact_id"] not in artifact_ids_to_remove]

print(data)

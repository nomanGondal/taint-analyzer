

        runs.append(
            {
                "agent_id": agent["id"],
                "agent_file": agent["path"],
                "project_id": body.get("project_id"),
                "issues_count": body.get("issues_count"),
                "summary": body.get("summary"),
                "pipeline": body.get("pipeline"),
                "rules_hit": sorted(rules_hit),
            }
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps({"manifest": manifest["description"], "runs": runs}, indent=2),
        encoding="utf-8",
    )

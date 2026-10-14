"""Agent 4: Data Processor MCP Server."""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class DataStats(BaseModel):
    """Statistics about processed data."""
    total_records: int = Field(description="Total number of records")
    valid_records: int = Field(description="Records that passed validation")
    invalid_records: int = Field(description="Records with validation errors")
    error_rate: float = Field(description="Percentage of invalid records")
    unique_values: int = Field(description="Count of unique values")


mcp = FastMCP(
    name="Data Processor Agent",
    instructions="Processes, validates, transforms, and aggregates data in various formats."
)


@mcp.tool()
def validate_data(data: list[dict], schema: dict | None = None) -> dict:
    """Validate data against a schema."""
    valid_records = 0
    invalid_records = 0
    unique_values = set()
    
    for record in data:
        is_valid = True
        if schema:
            for field in schema:
                if field not in record:
                    is_valid = False
                    break
        
        if is_valid:
            valid_records += 1
            for value in record.values():
                if isinstance(value, (str, int)):
                    unique_values.add(str(value))
        else:
            invalid_records += 1
    
    total = len(data)
    error_rate = (invalid_records / total * 100) if total > 0 else 0
    
    return {
        "total_records": total,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "error_rate": round(error_rate, 2),
        "unique_values": len(unique_values)
    }


@mcp.tool()
def transform_data(data: list[dict], transformation_type: str) -> dict:
    """Transform data between different formats."""
    if transformation_type == "flatten":
        result = []
        for record in data:
            flat = {}
            for key, value in record.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat[f"{key}_{sub_key}"] = sub_value
                else:
                    flat[key] = value
            result.append(flat)
        return {"success": True, "output_format": "flattened", "record_count": len(result)}
    
    return {"success": True, "output_format": "unchanged", "record_count": len(data)}


@mcp.tool()
def aggregate_data(data: list[dict], group_by: str | None = None) -> dict:
    """Aggregate data by grouping."""
    if not data or not group_by:
        return {"total_records": len(data), "groups": 1}
    
    groups = {}
    for record in data:
        group_key = record.get(group_by, "unknown")
        if group_key not in groups:
            groups[group_key] = 0
        groups[group_key] += 1
    
    return {"total_records": len(data), "groups": len(groups), "aggregation": groups}


@mcp.tool()
def convert_format(data, from_format: str, to_format: str) -> dict:
    """Convert data between different formats."""
    return {
        "from": from_format,
        "to": to_format,
        "success": True,
        "record_count": len(data) if isinstance(data, list) else 1
    }


@mcp.tool()
def detect_anomalies(data: list[dict], column: str | None = None) -> dict:
    """Detect anomalies in the data."""
    anomalies = []
    if data and column and column in data[0]:
        values = [r.get(column) for r in data if isinstance(r.get(column), (int, float))]
        if values:
            avg = sum(values) / len(values)
            std_dev = (sum((x - avg) ** 2 for x in values) / len(values)) ** 0.5
            for i, val in enumerate(values):
                if abs(val - avg) > 2 * std_dev:
                    anomalies.append({"index": i, "value": val})
    
    return {
        "total_records": len(data),
        "anomalies_found": len(anomalies),
        "anomaly_percentage": round(len(anomalies) / max(1, len(data)) * 100, 2)
    }


if __name__ == "__main__":
    mcp.run()

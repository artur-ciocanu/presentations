#!/usr/bin/env python3
"""Generate MongoDB $jsonSchema validator from the shared JSON Schema contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "schemas" / "agent-config.schema.json"
TARGET = ROOT / "schemas" / "agent-config.mongodb.schema.json"


def json_type_to_bson_type(type_value: str, format_value: str | None) -> str:
    if type_value == "string":
        # MongoDB stores timestamps as BSON Date values.
        if format_value == "date-time":
            return "date"
        return "string"
    if type_value == "integer":
        return "int"
    if type_value == "number":
        return "number"
    if type_value == "object":
        return "object"
    if type_value == "array":
        return "array"
    if type_value == "boolean":
        return "bool"
    if type_value == "null":
        return "null"
    raise ValueError(f"Unsupported JSON Schema type: {type_value}")


def convert_schema(schema: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {"bsonType": "object"}

    if "required" in schema:
        converted["required"] = schema["required"]

    properties = schema.get("properties", {})
    if properties:
        converted_properties: dict[str, Any] = {}
        for field_name, field_schema in properties.items():
            converted_properties[field_name] = convert_property(field_schema)
        converted["properties"] = converted_properties

    return converted


def convert_property(field_schema: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    field_type = field_schema.get("type")
    format_value = field_schema.get("format")

    if field_type:
        result["bsonType"] = json_type_to_bson_type(field_type, format_value)

    passthrough = [
        "enum",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "description",
    ]
    for key in passthrough:
        if key in field_schema:
            result[key] = field_schema[key]

    if field_type == "object" and "additionalProperties" in field_schema:
        result["additionalProperties"] = field_schema["additionalProperties"]

    if field_type == "array" and "items" in field_schema:
        result["items"] = convert_property(field_schema["items"])

    if field_type == "object" and "properties" in field_schema:
        result["properties"] = {
            name: convert_property(prop_schema)
            for name, prop_schema in field_schema["properties"].items()
        }
        if "required" in field_schema:
            result["required"] = field_schema["required"]

    return result


def main() -> None:
    with SOURCE.open("r", encoding="utf-8") as source_file:
        source_schema = json.load(source_file)

    mongo_schema = convert_schema(source_schema)

    with TARGET.open("w", encoding="utf-8") as target_file:
        json.dump(mongo_schema, target_file, indent=2)
        target_file.write("\n")

    print(f"Generated {TARGET.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Export the current FastAPI OpenAPI schema as an importable Postman v2.1 collection.

Run from server/: python -m scripts.export_postman
No credentials or live database content are included in the exported file.
"""

import json
import re
from pathlib import Path
from typing import Any

from app.main import app

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "SCosmetics.postman_collection.json"


def variable_name(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.title() for part in rest)


def example_for(schema: dict[str, Any], schemas: dict[str, Any], field: str = "", depth: int = 0) -> Any:
    if depth > 5:
        return None
    if "$ref" in schema:
        ref = schema["$ref"].rsplit("/", 1)[-1]
        return example_for(schemas.get(ref, {}), schemas, field, depth + 1)
    for branch in ("anyOf", "oneOf", "allOf"):
        if branch in schema:
            non_null = next((item for item in schema[branch] if item.get("type") != "null"), {})
            return example_for(non_null, schemas, field, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "examples" in schema and schema["examples"]:
        return schema["examples"][0]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if schema.get("type") == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        return {
            key: example_for(properties[key], schemas, key, depth + 1)
            for key in required if key in properties
        }
    if schema.get("type") == "array":
        return [example_for(schema.get("items", {}), schemas, field, depth + 1)]
    if field == "email":
        return "{{email}}"
    if field in {"password", "password_confirmation"}:
        return "{{password}}"
    if field == "refresh_token":
        return "{{refreshToken}}"
    if field in {"first_name", "last_name"}:
        return "Demo" if field == "first_name" else "Customer"
    if field == "phone":
        return "0500000000"
    if field.endswith("_id"):
        return "{{" + variable_name(field) + "}}"
    if schema.get("format") == "date-time":
        return "{{startTime}}"
    if schema.get("format") == "date":
        return "{{date}}"
    if schema.get("format") == "email":
        return "{{email}}"
    if schema.get("type") == "integer":
        return 1
    if schema.get("type") == "number":
        return 1
    if schema.get("type") == "boolean":
        return True
    if schema.get("type") == "string":
        return "example"
    return None


def request_for(path: str, method: str, operation: dict[str, Any], schemas: dict[str, Any]) -> dict[str, Any]:
    path_parameters = re.findall(r"\{([^}]+)\}", path)
    postman_path = re.sub(r"\{([^}]+)\}", lambda match: ":" + match.group(1), path)
    parameters = operation.get("parameters", [])
    query = [
        {
            "key": param["name"],
            "value": "{{" + variable_name(param["name"]) + "}}",
            "disabled": not param.get("required", False),
            "description": "Required" if param.get("required") else "Optional",
        }
        for param in parameters if param.get("in") == "query"
    ]
    url: dict[str, Any] = {
        "raw": "{{baseUrl}}" + postman_path + (
            "?" + "&".join(f"{item['key']}={item['value']}" for item in query if not item["disabled"])
            if any(not item["disabled"] for item in query) else ""
        ),
        "host": ["{{baseUrl}}"],
        "path": [segment for segment in postman_path.split("/") if segment],
    }
    if query:
        url["query"] = query
    if path_parameters:
        url["variable"] = [
            {"key": name, "value": "{{" + variable_name(name) + "}}"}
            for name in path_parameters
        ]
    request: dict[str, Any] = {
        "method": method.upper(),
        "header": [],
        "auth": (
            {"type": "bearer", "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}]}
            if operation.get("security") else {"type": "noauth"}
        ),
        "url": url,
        "description": operation.get("description") or operation.get("summary", ""),
    }
    body = operation.get("requestBody", {}).get("content", {})
    if "application/json" in body:
        sample = example_for(body["application/json"].get("schema", {}), schemas)
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": json.dumps(sample, ensure_ascii=False, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    item: dict[str, Any] = {
        "name": f"{method.upper()} {postman_path}",
        "request": request,
        "response": [],
    }
    if path == "/api/v1/auth/login" and method == "post":
        item["event"] = [{
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "if (pm.response.code === 200 && pm.environment) {",
                    "  const tokens = pm.response.json();",
                    "  pm.environment.set('accessToken', tokens.access_token);",
                    "  pm.environment.set('refreshToken', tokens.refresh_token);",
                    "}",
                ],
            },
        }]
    return item


def build_collection() -> dict[str, Any]:
    openapi = app.openapi()
    schemas = openapi.get("components", {}).get("schemas", {})
    folders: dict[str, list[dict[str, Any]]] = {}
    for path, operations in openapi["paths"].items():
        for method in HTTP_METHODS:
            if method in operations:
                operation = operations[method]
                tag = (operation.get("tags") or ["other"])[0]
                folders.setdefault(tag, []).append(request_for(path, method, operation, schemas))
    variable_defaults = {"baseUrl": "http://127.0.0.1:8004"}
    for requests in folders.values():
        for item in requests:
            for name in re.findall(r"\{\{([A-Za-z][A-Za-z0-9]*)\}\}", json.dumps(item)):
                variable_defaults.setdefault(name, "")
    return {
        "info": {
            "name": "SCosmetics API",
            "description": "Generated from FastAPI OpenAPI. Examples are placeholders; do not export live credentials.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [{"name": tag, "item": requests} for tag, requests in folders.items()],
        "variable": [{"key": key, "value": value} for key, value in variable_defaults.items()],
    }


def main() -> None:
    collection = build_collection()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {sum(len(folder['item']) for folder in collection['item'])} requests to {OUTPUT}")


if __name__ == "__main__":
    main()

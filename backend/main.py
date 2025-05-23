
from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import yaml
import json
import httpx
from typing import Dict, Any

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://localhost(:[0-9]+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)

tools_metadata = []
mcp_tools = []

API_ROOT = "https://api.incubation-demo.cp.fyre.ibm.com:6443"

class OpenAPISpec(BaseModel):
    content: str

def parse_openapi_spec(content: str) -> Dict[str, Any]:
    try:
        return yaml.safe_load(content)
    except Exception as e:
        raise ValueError(f"Failed to parse OpenAPI/Swagger spec: {e}")

def convert_operation_to_mcp_tool(path: str, method: str, operation: dict, route_name: str) -> Dict[str, Any]:
    parameters = operation.get("parameters", [])
    request_body = operation.get("requestBody", {})
    responses = operation.get("responses", {})
    props = {}
    required = []

    for param in parameters:
        name = param["name"]
        schema = param.get("schema", {"type": "string"})
        props[name] = {
            "type": schema.get("type", "string"),
            "description": param.get("description", "")
        }
        if param.get("required"):
            required.append(name)

    if request_body:
        content = request_body.get("content", {})
        json_schema = content.get("application/json", {}).get("schema", {})
        if json_schema.get("type") == "object":
            for k, v in json_schema.get("properties", {}).items():
                props[k] = {
                    "type": v.get("type", "string"),
                    "description": v.get("description", "")
                }
            required += json_schema.get("required", [])

    response_schemas = {}
    for status_code, response in responses.items():
        description = response.get("description", "")
        # Swagger 2.0 uses 'examples' directly
        examples = response.get("examples", {})
        response_schemas[status_code] = {
            "description": description,
            "examples": examples
        }
    print(response_schemas)

    return {
        "name": route_name,
        "description": operation.get("description", "No summary"),
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required
        },
        "responses": response_schemas
    }

@app.post("/tools")
async def get_tools(spec: OpenAPISpec):
    global tools_metadata, mcp_tools
    tools_metadata.clear()
    mcp_tools.clear()

    try:
        parsed_spec = parse_openapi_spec(spec.content)
        is_openapi = "openapi" in parsed_spec
        is_swagger = "swagger" in parsed_spec

        if is_openapi:
            server_url = parsed_spec.get("servers", [{}])[0].get("url", "")
        elif is_swagger:
            base_path = parsed_spec.get("basePath", "")
        else:
            raise ValueError("Spec is neither OpenAPI nor Swagger")

        # Create real proxy handler
        def make_proxy_handler(full_target_url: str, method: str, route_name: str):
            async def proxy_handler(request: Request, body: dict = Body(default=None)):
                try:
                    async with httpx.AsyncClient(verify=False) as client:
                        response = await client.request(
                            method=method.upper(),
                            url=full_target_url,
                            params=dict(request.query_params),
                            json=body if body else None,
                            headers={"Content-Type": "application/json"},
                        )
                    return JSONResponse(status_code=response.status_code, content=response.json())
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Proxy failed for {route_name}", "detail": str(e)}
                    )
            return proxy_handler

        # Add each path/method
        for path, path_item in parsed_spec.get("paths", {}).items():
            for method, operation in path_item.items():
                route_name = operation.get("operationId", f"{method}_{path}")
                tool_schema = convert_operation_to_mcp_tool(path, method, operation, route_name)

                # Construct full backend URL
                full_target_url = ""
                if is_openapi:
                    full_target_url = f"{server_url.rstrip('/')}{path}"
                elif is_swagger:
                    full_target_url = f"{base_path}{path}"
                print(f"Full target URL: {full_target_url}")
                # Register FastAPI proxy
                app.add_api_route(
                    path=path,
                    endpoint=make_proxy_handler(full_target_url, method, route_name),
                    methods=[method.upper()],
                    name=route_name,
                )

                tools_metadata.append({
                    "name": route_name,
                    "description": operation.get("description", ""),
                    "path": path,
                    "method": method.upper(),
                    "parameters": tool_schema["parameters"],
                    "responses": tool_schema["responses"]
                })
                mcp_tools.append(tool_schema)

        return tools_metadata

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": "Failed to process spec", "detail": str(e)}
        )

@app.get("/mcp-tools")
async def get_mcp_tools():
    return mcp_tools

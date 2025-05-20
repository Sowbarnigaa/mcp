
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# import json
# import yaml
# from typing import Dict, Any
# import re

# app = FastAPI()

# # Allow CORS from any localhost port
# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=r"^http://localhost(:[0-9]+)?$",
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Load OpenAPI Spec
# def load_openapi_spec(path: str) -> Dict[str, Any]:
#     with open(path, "r") as f:
#         if path.endswith(".yaml") or path.endswith(".yml"):
#             return yaml.safe_load(f)
#         return json.load(f)

# spec = load_openapi_spec("openapi.yaml")
# tools_metadata = []
# mcp_tools = []

# # Convert OpenAPI operation to schema
# def convert_operation_to_mcp_tool(path: str, method: str, operation: dict, route_name: str) -> Dict[str, Any]:
#     parameters = operation.get("parameters", [])
#     request_body = operation.get("requestBody", {})
#     props = {}
#     required = []

#     for param in parameters:
#         name = param["name"]
#         schema = param.get("schema", {"type": "string"})
#         props[name] = {
#             "type": schema.get("type", "string"),
#             "description": param.get("description", "")
#         }
#         if param.get("required"):
#             required.append(name)

#     if request_body:
#         content = request_body.get("content", {})
#         json_schema = content.get("application/json", {}).get("schema", {})
#         if json_schema.get("type") == "object":
#             for k, v in json_schema.get("properties", {}).items():
#                 props[k] = {
#                     "type": v.get("type", "string"),
#                     "description": v.get("description", "")
#                 }
#             required += json_schema.get("required", [])

#     return {
#         "name": route_name,
#         "description": operation.get("summary", "No summary"),
#         "parameters": {
#             "type": "object",
#             "properties": props,
#             "required": required
#         }
#     }

# # Create a FastAPI route handler
# def create_tool_endpoint(path: str, method: str, operation: dict):
#     async def tool(request: Request):
#         try:
#             body = {}
#             if method in ["post", "put", "patch"]:
#                 content_type = request.headers.get("content-type", "")
#                 if "application/json" in content_type:
#                     body = await request.json()
#                 elif "application/x-www-form-urlencoded" in content_type:
#                     form = await request.form()
#                     body = dict(form)
#                 else:
#                     return JSONResponse(
#                         status_code=415,
#                         content={
#                             "error": "Unsupported Media Type",
#                             "detail": f"Unsupported Content-Type: {content_type}"
#                         }
#                     )
#             else:
#                 body = dict(request.query_params)

#             return {
#                 "tool_path": path,
#                 "method": method.upper(),
#                 "operation_summary": operation.get("summary", "No summary"),
#                 "received_path_params": request.path_params,
#                 "received_query_or_body": body
#             }

#         except Exception as e:
#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "error": "Internal Server Error",
#                     "detail": str(e)
#                 }
#             )

#     return tool

# # Register tools from OpenAPI spec
# def register_tools():
#     global tools_metadata, mcp_tools
#     for path, path_item in spec.get("paths", {}).items():
#         for method in path_item:
#             operation = path_item[method]
#             route_name = operation.get("operationId", f"{method}_{path}")
#             handler = create_tool_endpoint(path, method, operation)
#             app.add_api_route(path, handler, methods=[method.upper()], name=route_name)

#             # Tool metadata with schema (for frontend UI generation)
#             tool_schema = convert_operation_to_mcp_tool(path, method, operation, route_name)
#             tools_metadata.append({
#                 "name": route_name,
#                 "description": operation.get("summary", "No summary"),
#                 "path": path,
#                 "method": method.upper(),
#                 "parameters": tool_schema["parameters"]
#             })
#             mcp_tools.append(tool_schema)

# # Register tools on startup
# register_tools()

# @app.get("/tools")
# async def get_tools():
#     return tools_metadata

# @app.get("/mcp-tools")
# async def get_mcp_tools():
#     return mcp_tools


# Implementation of backend here and frontend from studio ui post call with open api spec file content as request body
from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import yaml
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

class OpenAPISpec(BaseModel):
    content: str

def parse_openapi_spec(content: str) -> Dict[str, Any]:
    try:
        return yaml.safe_load(content)
    except Exception as e:
        raise ValueError(f"Failed to parse OpenAPI spec: {e}")

def convert_operation_to_mcp_tool(path: str, method: str, operation: dict, route_name: str) -> Dict[str, Any]:
    parameters = operation.get("parameters", [])
    request_body = operation.get("requestBody", {})
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

    return {
        "name": route_name,
        "description": operation.get("description", "No summary"),
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required
        }
    }

@app.post("/tools")
async def get_tools(spec: OpenAPISpec):
    global tools_metadata, mcp_tools
    tools_metadata.clear()
    mcp_tools.clear()

    try:
        parsed_spec = parse_openapi_spec(spec.content)

        def make_actual_handler(route_name):
            async def handler(request: Request, body: dict = Body(default=None)):
                return {
                    "operation": route_name,
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": dict(request.query_params),
                    "body": body,
                }
            return handler

        for path, path_item in parsed_spec.get("paths", {}).items():
            for method, operation in path_item.items():
                print(operation.get("description"))
                route_name = operation.get("operationId", f"{method}_{path}")
                handler = make_actual_handler(route_name)

                app.add_api_route(
                    path=path,
                    endpoint=handler,
                    methods=[method.upper()],
                    name=route_name
                )

                tool_schema = convert_operation_to_mcp_tool(path, method, operation, route_name)

                tools_metadata.append({
                    "name": route_name,
                    "description": operation.get("description"),
                    "path": path,
                    "method": method.upper(),
                    "parameters": tool_schema["parameters"]
                })

                mcp_tools.append(tool_schema)

        return tools_metadata

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": "Failed to parse or process OpenAPI spec", "detail": str(e)}
        )

# # from fastapi import FastAPI, Request
# # from fastapi.middleware.cors import CORSMiddleware
# # import json
# # import yaml
# # from typing import Dict, Any

# # app = FastAPI()

# # # Allow CORS for frontend running on localhost:3000
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["http://localhost:3000"],
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # def load_openapi_spec(path: str) -> Dict[str, Any]:
# #     with open(path, "r") as f:
# #         if path.endswith(".yaml") or path.endswith(".yml"):
# #             return yaml.safe_load(f)
# #         else:
# #             return json.load(f)

# # # Load spec on startup
# # spec = load_openapi_spec("openapi.yaml")

# # # Store tool metadata for frontend
# # tools_metadata = []

# # def create_tool_endpoint(path: str, method: str, operation: dict):
# #     async def tool(request: Request):
# #         # Get JSON body or query params depending on method
# #         if method in ["post", "put", "patch"]:
# #             try:
# #                 body = await request.json()
# #             except Exception:
# #                 body = None
# #         else:
# #             body = None
        
# #         # Just echo what we got + tool info for demo
# #         return {
# #             "tool_path": path,
# #             "method": method.upper(),
# #             "operation_summary": operation.get("summary", "No summary"),
# #             "received_body": body,
# #             "query_params": dict(request.query_params),
# #         }
# #     return tool

# # def fastapi_path_from_openapi_path(openapi_path: str):
# #     # Convert OpenAPI params {id} -> FastAPI style {id}
# #     # (They are the same syntax, but just ensure no conflicts)
# #     return openapi_path

# # @app.on_event("startup")
# # def register_tools():
# #     paths = spec.get("paths", {})
# #     for path, methods in paths.items():
# #         for method, operation in methods.items():
# #             endpoint = create_tool_endpoint(path, method, operation)
# #             fastapi_path = fastapi_path_from_openapi_path(path)
# #             route_name = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")
# #             app.add_api_route(
# #                 fastapi_path,
# #                 endpoint,
# #                 methods=[method.upper()],
# #                 name=route_name,
# #             )
# #             tools_metadata.append({
# #                 "path": path,
# #                 "method": method.upper(),
# #                 "summary": operation.get("summary", ""),
# #                 "route_name": route_name,
# #             })

# # @app.get("/tools")
# # async def get_tools():
# #     """Return list of tools (endpoints) for frontend"""
# #     return tools_metadata

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# import json
# import yaml
# from typing import Dict, Any
# from pydantic import BaseModel

# app = FastAPI()

# # Allow CORS for frontend running on localhost:3000
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# def load_openapi_spec(path: str) -> Dict[str, Any]:
#     with open(path, "r") as f:
#         if path.endswith(".yaml") or path.endswith(".yml"):
#             return yaml.safe_load(f)
#         else:
#             return json.load(f)

# spec = load_openapi_spec("openapi.yaml")
# tools_metadata = []
# mcp_tools = []

# def convert_operation_to_mcp_tool(path: str, method: str, operation: dict, route_name: str) -> Dict[str, Any]:
#     """Convert OpenAPI operation to an MCP tool definition."""
#     parameters = operation.get("parameters", [])
#     request_body = operation.get("requestBody", {})
#     props = {}
#     required = []

#     # Handle query/path/header parameters
#     for param in parameters:
#         name = param["name"]
#         schema = param.get("schema", {"type": "string"})
#         props[name] = {
#             "type": schema.get("type", "string"),
#             "description": param.get("description", "")
#         }
#         if param.get("required"):
#             required.append(name)

#     # Handle request body
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

# def create_tool_endpoint(path: str, method: str, operation: dict):
#     async def tool(request: Request):
#         if method in ["post", "put", "patch"]:
#             try:
#                 body = await request.json()
#             except Exception:
#                 body = {}
#         else:
#             body = dict(request.query_params)

#         return {
#             "tool_path": path,
#             "method": method.upper(),
#             "operation_summary": operation.get("summary", "No summary"),
#             "received_body": body
#         }

#     return tool

# def fastapi_path_from_openapi_path(openapi_path: str):
#     return openapi_path  # Currently 1:1, but could extend for custom parsing

# @app.on_event("startup")
# def register_tools():
#     paths = spec.get("paths", {})
#     for path, methods in paths.items():
#         for method, operation in methods.items():
#             endpoint = create_tool_endpoint(path, method, operation)
#             fastapi_path = fastapi_path_from_openapi_path(path)
#             route_name = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")

#             app.add_api_route(
#                 fastapi_path,
#                 endpoint,
#                 methods=[method.upper()],
#                 name=route_name,
#             )

#             tools_metadata.append({
#                 "path": path,
#                 "method": method.upper(),
#                 "summary": operation.get("summary", ""),
#                 "route_name": route_name,
#             })

#             # Convert and store as MCP tool
#             mcp_tool = convert_operation_to_mcp_tool(path, method, operation, route_name)
#             mcp_tools.append(mcp_tool)

# @app.get("/tools")
# async def get_tools():
#     """Return list of registered API endpoints (tools)."""
#     return tools_metadata

# @app.get("/mcp-tools")
# async def get_mcp_tools():
#     """Return list of tools in MCP format for AI agents."""
#     return mcp_tools

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import yaml
from typing import Dict, Any
import re

app = FastAPI()

# Allow CORS from any localhost port
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://localhost(:[0-9]+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAPI Spec
def load_openapi_spec(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        if path.endswith(".yaml") or path.endswith(".yml"):
            return yaml.safe_load(f)
        return json.load(f)

spec = load_openapi_spec("openapi.yaml")
tools_metadata = []
mcp_tools = []

# Convert OpenAPI operation to schema
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
        "description": operation.get("summary", "No summary"),
        "parameters": {
            "type": "object",
            "properties": props,
            "required": required
        }
    }

# Create a FastAPI route handler
def create_tool_endpoint(path: str, method: str, operation: dict):
    async def tool(request: Request):
        try:
            body = {}
            if method in ["post", "put", "patch"]:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    body = await request.json()
                elif "application/x-www-form-urlencoded" in content_type:
                    form = await request.form()
                    body = dict(form)
                else:
                    return JSONResponse(
                        status_code=415,
                        content={
                            "error": "Unsupported Media Type",
                            "detail": f"Unsupported Content-Type: {content_type}"
                        }
                    )
            else:
                body = dict(request.query_params)

            return {
                "tool_path": path,
                "method": method.upper(),
                "operation_summary": operation.get("summary", "No summary"),
                "received_path_params": request.path_params,
                "received_query_or_body": body
            }

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": str(e)
                }
            )

    return tool

# Register tools from OpenAPI spec
def register_tools():
    global tools_metadata, mcp_tools
    for path, path_item in spec.get("paths", {}).items():
        for method in path_item:
            operation = path_item[method]
            route_name = operation.get("operationId", f"{method}_{path}")
            handler = create_tool_endpoint(path, method, operation)
            app.add_api_route(path, handler, methods=[method.upper()], name=route_name)

            # Tool metadata with schema (for frontend UI generation)
            tool_schema = convert_operation_to_mcp_tool(path, method, operation, route_name)
            tools_metadata.append({
                "name": route_name,
                "description": operation.get("summary", "No summary"),
                "path": path,
                "method": method.upper(),
                "parameters": tool_schema["parameters"]
            })
            mcp_tools.append(tool_schema)

# Register tools on startup
register_tools()

@app.get("/tools")
async def get_tools():
    return tools_metadata

@app.get("/mcp-tools")
async def get_mcp_tools():
    return mcp_tools

import React, { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [pathParams, setPathParams] = useState({});
  const [queryParams, setQueryParams] = useState({});
  const [body, setBody] = useState("{}");
  const [response, setResponse] = useState(null);

  useEffect(() => {
    axios.get("http://localhost:8000/tools").then((res) => {
      setTools(res.data);
    });
  }, []);

  const handleSelectTool = (tool) => {
    setSelectedTool(tool);
    setPathParams({});
    setQueryParams({});
    setBody("{}");
    setResponse(null);
  };

  // Simple function to parse path params like {msg} in path /echo/{msg}
  const getPathParams = () => {
    if (!selectedTool) return [];
    const regex = /{([^}]+)}/g;
    const matches = [...selectedTool.path.matchAll(regex)];
    return matches.map((m) => m[1]);
  };

  // Compose URL with path params replaced
  const composeUrl = () => {
    if (!selectedTool) return "";
    let url = selectedTool.path;
    getPathParams().forEach((param) => {
      url = url.replace(`{${param}}`, encodeURIComponent(pathParams[param] || ""));
    });

    // Add query params if GET or similar
    if (selectedTool.method === "GET" && Object.keys(queryParams).length > 0) {
      const qp = new URLSearchParams(queryParams).toString();
      url += "?" + qp;
    }
    return url;
  };

  const sendRequest = async () => {
    if (!selectedTool) return;

    const url = "http://localhost:8000" + composeUrl();

    try {
      const method = selectedTool.method.toLowerCase();

      let data = null;
      try {
        data = JSON.parse(body);
      } catch {
        alert("Body is not valid JSON");
        return;
      }

      const config = {
        method,
        url,
      };

      if (["post", "put", "patch"].includes(method)) {
        config.data = data;
      }

      const res = await axios(config);
      setResponse(res.data);
    } catch (e) {
      setResponse({ error: e.message });
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>MCP Tool Runner</h1>
      <h2>Available Tools:</h2>
      <ul>
        {tools.map((tool) => (
          <li key={tool.route_name}>
            <button onClick={() => handleSelectTool(tool)}>
              [{tool.method}] {tool.path} - {tool.summary}
            </button>
          </li>
        ))}
      </ul>

      {selectedTool && (
        <>
          <h2>Run Tool: [{selectedTool.method}] {selectedTool.path}</h2>

          {getPathParams().length > 0 && (
            <>
              <h3>Path Parameters</h3>
              {getPathParams().map((param) => (
                <div key={param}>
                  <label>{param}: </label>
                  <input
                    type="text"
                    value={pathParams[param] || ""}
                    onChange={(e) =>
                      setPathParams({ ...pathParams, [param]: e.target.value })
                    }
                  />
                </div>
              ))}
            </>
          )}

          {selectedTool.method === "GET" && (
            <>
              <h3>Query Parameters (JSON object)</h3>
              <textarea
                rows={4}
                cols={50}
                value={JSON.stringify(queryParams, null, 2)}
                onChange={(e) => {
                  try {
                    setQueryParams(JSON.parse(e.target.value));
                  } catch {
                    // ignore invalid JSON
                  }
                }}
              />
            </>
          )}

          {["POST", "PUT", "PATCH"].includes(selectedTool.method) && (
            <>
              <h3>Request Body (JSON)</h3>
              <textarea
                rows={8}
                cols={50}
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            </>
          )}
          <></>
          <button onClick={sendRequest} className="mr-8">Send Request</button>

          {response && (
            <>
              <h3>Response:</h3>
              <pre>{JSON.stringify(response, null, 2)}</pre>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default App;

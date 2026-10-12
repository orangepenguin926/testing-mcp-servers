# Manipal Hospitals India MCP

Transport is chosen by env var: default `streamable-http` (endpoint `/mcp`, needed by Agentforce);
`TRANSPORT=stdio` for Claude Desktop.

    pip install -r requirements.txt
    python server.py                 # http://localhost:8000/mcp
    TRANSPORT=stdio python server.py # local stdio

## Deploy (Agentforce needs a public HTTPS URL)
Docker: `docker build -t manipal-mcp . && docker run -p 8080:8080 manipal-mcp`
Deploy on Render / Fly.io / Cloud Run / Azure Container Apps -> URL like https://<host>/mcp
Quick test: `ngrok http 8000` -> https://<id>.ngrok-free.app/mcp

## Agentforce
1. Setup -> Agentforce Registry -> New -> enter the server URL (https://<host>/mcp); pick "no auth" for this public read-only demo, or OAuth 2.0 if you put the server behind an OAuth-protected gateway.
2. Select tools to register (start with list_hospitals, search_hospitals, get_hospital, list_cities). Each becomes an action in the Asset Library.
3. Add the actions to a subagent in Agentforce Builder and give each a clear instruction, e.g. "Use list_hospitals when the customer asks for Manipal hospitals in a city."
4. Test in the Builder preview: "Which Manipal hospitals are in Pune?"

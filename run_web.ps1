# PowerShell script to run the ADK Web playground with CORS allowed origins enabled
Write-Host "Starting ADK Web Playground..."
uv run adk web --host 127.0.0.1 --port 8085 --reload_agents --allow_origins "regex:.*"

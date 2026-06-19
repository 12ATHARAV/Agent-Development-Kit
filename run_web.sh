#!/bin/bash
# Shell script to run the ADK Web playground with CORS allowed origins enabled
echo "Starting ADK Web Playground..."
uv run adk web --host 127.0.0.1 --port 8085 --reload_agents --allow_origins "regex:.*"

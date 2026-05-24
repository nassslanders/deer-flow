#!/bin/sh
set -e
ln -sf /app/config.yaml /app/backend/config.yaml
echo "[START] Patching auth_middleware.py..."
python3 /startup/patch_auth.py
echo "[START] Patching app.py for /api/langgraph routes..."
python3 /startup/patch_app.py
ADMIN_ID="d863b8eb-6211-4792-b93f-251ea15d2d68"
AGENT_DIR="/app/backend/.deer-flow/users/${ADMIN_ID}/agents/agent"
mkdir -p "${AGENT_DIR}"
if [ ! -f "${AGENT_DIR}/config.yaml" ]; then
  echo "name: agent" > "${AGENT_DIR}/config.yaml"
fi
if [ ! -f "${AGENT_DIR}/SOUL.md" ]; then
  echo "# Agent Soul" > "${AGENT_DIR}/SOUL.md"
fi
echo "[START] Agent directory ready"
echo "[START] Starting uvicorn..."
cd /app/backend
exec uv run --no-sync uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001

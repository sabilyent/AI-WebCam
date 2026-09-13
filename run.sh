#!/usr/bin/env bash
# AI-WebCam Startup Script
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================="
echo "🎥 Memulakan Sistem AI-WebCam..."
echo "=================================================="

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "📦 Mencipta persekitaran maya Python (.venv)..."
    if command -v /home/miqa/.local/bin/uv &> /dev/null; then
        /home/miqa/.local/bin/uv venv --python 3.10 .venv
        /home/miqa/.local/bin/uv pip install -r requirements.txt
    else
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt
    fi
fi

# Activate venv and run
source .venv/bin/activate
echo "🚀 Pelayan sedia di http://127.0.0.1:5000"
exec python app.py

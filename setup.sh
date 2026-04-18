#!/usr/bin/env bash
set -e

echo "=== Media Library Setup ==="

# --- System deps ---
if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y ffmpeg python3-pip python3-venv nodejs npm
elif command -v brew &>/dev/null; then
  brew install ffmpeg node
fi

# --- Backend ---
echo ""
echo "--- Setting up backend ---"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
deactivate
cd ..

# --- Frontend ---
echo ""
echo "--- Setting up frontend ---"
cd frontend
npm install
cd ..

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start backend:  cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo "Start frontend: cd frontend && npm run dev"
echo ""
echo "Or for production build:"
echo "  cd frontend && npm run build"
echo "  cd backend && source .venv/bin/activate && uvicorn main:app"

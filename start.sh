#!/bin/bash
# VERA Bot — Quick Start Script
# Run this from the project root: bash start.sh

set -e

echo "🤖 VERA Bot — Quick Start"
echo "========================="

# Check Python
PYTHON=""
for p in python3 python3.11 python; do
    if command -v "$p" &>/dev/null; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python not found. Install Python 3.9+"
    exit 1
fi

echo "✅ Python: $PYTHON ($($PYTHON --version 2>&1))"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
$PYTHON -m pip install --upgrade pip -q 2>/dev/null || true
$PYTHON -m pip install fastapi uvicorn[standard] pydantic -q

echo "✅ Dependencies installed"

# Check for API key
if [ -z "$GEMINI_API_KEY" ] && [ -z "$LLM_API_KEY" ]; then
    echo ""
    echo "⚠️  No API key found!"
    echo "   Set one of these environment variables:"
    echo "   export GEMINI_API_KEY='your-key'    # For Gemini (default)"
    echo "   export OPENAI_API_KEY='your-key'     # For OpenAI"
    echo "   export LLM_API_KEY='your-key'        # Generic"
    echo ""
    echo "   Get a free Gemini key at: https://aistudio.google.com/apikey"
    echo ""
    read -p "Enter your Gemini API key (or press Enter to skip): " key
    if [ -n "$key" ]; then
        export GEMINI_API_KEY="$key"
        export LLM_API_KEY="$key"
        echo "✅ API key set"
    fi
fi

# Generate expanded dataset if not exists
if [ ! -d "dataset/expanded" ]; then
    echo ""
    echo "📊 Generating expanded dataset..."
    $PYTHON dataset/generate_dataset.py --seed-dir dataset --out dataset/expanded
    echo "✅ Dataset generated"
fi

# Start the server
PORT=${PORT:-8080}
echo ""
echo "🚀 Starting VERA Bot on port $PORT..."
echo "   Health: http://localhost:$PORT/v1/healthz"
echo "   Docs:   http://localhost:$PORT/docs"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

$PYTHON -m uvicorn bot:app --host 0.0.0.0 --port $PORT --reload

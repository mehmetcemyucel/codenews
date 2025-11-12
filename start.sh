#!/bin/bash

# CodeNews Startup Script

echo "🤖 Starting CodeNews..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please run:"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your configuration"
    exit 1
fi

# Check if database exists, if not initialize it
if [ ! -f "data/codenews.db" ]; then
    echo "📊 Initializing database..."
    python -c "from src.database import init_db; init_db()"
fi

# Start the application
echo "✅ Starting CodeNews application..."
python src/main.py

#!/bin/bash

# Life Copilot Backend Setup Script

echo "🚀 Setting up Life Copilot Backend..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - GOOGLE_CLIENT_ID (optional)"
    echo "   - GOOGLE_CLIENT_SECRET (optional)"
    echo ""
fi

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL..."
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start it first."
    echo "   On macOS with Postgres.app: Just open the app"
    echo "   Or with Homebrew: brew services start postgresql"
    exit 1
fi

# Check if Redis is running
echo "🔍 Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis is not running. Starting Redis..."
    echo "   On macOS: brew services start redis"
    echo "   Or run: redis-server &"
fi

# Create database
echo "📦 Creating database..."
createdb life_copilot 2>/dev/null || echo "Database already exists"

# Run migrations
echo "🔄 Running database migrations..."
source venv/bin/activate
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "To start the backend:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To start Celery worker (in another terminal):"
echo "  source venv/bin/activate"
echo "  celery -A app.tasks.celery_app worker --loglevel=info"

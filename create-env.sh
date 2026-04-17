#!/bin/bash

# Script to create .env file with secure defaults

echo "🔐 Creating .env file..."

# Generate a secure SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create .env file
cat > .env << EOF
# Application
APP_NAME=Life Copilot
DEBUG=true
ENVIRONMENT=development

# Security
SECRET_KEY=${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/life_copilot

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# OpenAI (REQUIRED - ADD YOUR KEY HERE!)
OPENAI_API_KEY=sk-your-openai-api-key-here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Vector Store
VECTOR_STORE_PATH=./data/vector_store

# API
API_V1_PREFIX=/api/v1
EOF

echo "✅ .env file created!"
echo ""
echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key:"
echo "   OPENAI_API_KEY=sk-your-actual-key-here"
echo ""
echo "Get your API key from: https://platform.openai.com/api-keys"

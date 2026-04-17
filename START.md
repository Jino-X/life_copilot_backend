# 🚀 Quick Start Guide

## Prerequisites Checklist

- ✅ Python 3.14 installed
- ✅ PostgreSQL running
- ✅ Redis running (optional for development)
- ⚠️ OpenAI API key (required)

## Step-by-Step Setup

### 1. Environment Setup

The `.env` file has been created for you. **You MUST add your OpenAI API key:**

```bash
# Edit the .env file
nano .env  # or use your preferred editor
```

Find this line and replace with your actual API key:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 2. Create Database

```bash
createdb life_copilot
```

If you get "database already exists", that's fine!

### 3. Run Database Migrations

```bash
source venv/bin/activate
alembic upgrade head
```

### 4. Start the Server

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: **http://localhost:8000**

### 5. Check if it's working

Open your browser and visit:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Optional: Start Background Workers

### Celery Worker (for background tasks)
```bash
# In a new terminal
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

### Celery Beat (for scheduled tasks)
```bash
# In another terminal
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info
```

## Common Issues

### Issue: "ModuleNotFoundError"
**Solution:** Make sure you activated the virtual environment:
```bash
source venv/bin/activate
```

### Issue: "Database connection failed"
**Solution:** Make sure PostgreSQL is running and the database exists:
```bash
# Check if PostgreSQL is running
pg_isready

# Create database if needed
createdb life_copilot
```

### Issue: "OpenAI API error"
**Solution:** Check that your API key is correct in `.env` file

### Issue: "Redis connection failed"
**Solution:** Redis is optional for basic development. To start Redis:
```bash
brew services start redis
# or
redis-server
```

## What's Next?

1. **Test the API** - Visit http://localhost:8000/docs
2. **Create a user** - Use the `/api/v1/auth/register` endpoint
3. **Get a token** - Use the `/api/v1/auth/login` endpoint
4. **Try the AI features** - Use the chat endpoints

## Need Help?

- Check the main README.md for full documentation
- Review the API docs at http://localhost:8000/docs
- Check logs for error messages

---

**Pro Tip:** Keep the server running in one terminal and use another terminal for testing!

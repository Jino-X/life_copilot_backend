# Life Copilot - Backend API

AI-powered personal assistant backend built with FastAPI, featuring intelligent task management, habit tracking, calendar integration, email management, and conversational AI.

## 🚀 Features

- **Authentication & Authorization**: JWT-based secure authentication
- **Task Management**: AI-powered task breakdown and intelligent scheduling
- **Habit Tracking**: Daily habit monitoring with streak tracking
- **Calendar Integration**: Event management and scheduling
- **Email Management**: Gmail integration with AI-powered email analysis
- **Notes**: Organized note-taking with search capabilities
- **AI Chat**: Conversational AI assistant powered by OpenAI
- **Vector Store**: Semantic search using ChromaDB
- **Multi-Agent System**: Specialized AI agents for different tasks

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy (async)
- **AI**: OpenAI GPT-4, LangChain
- **Vector Store**: ChromaDB
- **Authentication**: JWT tokens with bcrypt
- **Email**: Gmail API integration
- **Task Queue**: Background task processing

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 14+
- OpenAI API key
- Google Cloud credentials (for Gmail integration)

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Jino-X/life_copilot_backend.git
cd life_copilot_backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements-minimal.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lifecopilot

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Google OAuth (Optional - for Gmail integration)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 5. Initialize database

```bash
# Create database tables
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🗂️ Project Structure

```
backend/
├── app/
│   ├── agents/              # AI agent implementations
│   │   ├── base.py
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   ├── task_agent.py
│   │   └── email_agent.py
│   ├── api/
│   │   └── v1/             # API endpoints
│   │       ├── auth.py
│   │       ├── tasks.py
│   │       ├── habits.py
│   │       ├── calendar.py
│   │       ├── emails.py
│   │       ├── notes.py
│   │       └── chat.py
│   ├── core/               # Core configurations
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/             # Database models
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── habit.py
│   │   ├── calendar_event.py
│   │   ├── email.py
│   │   ├── note.py
│   │   └── chat.py
│   ├── services/           # Business logic
│   │   ├── task_service.py
│   │   ├── habit_service.py
│   │   ├── calendar_service.py
│   │   ├── email_service.py
│   │   ├── note_service.py
│   │   └── chat_service.py
│   └── main.py            # Application entry point
├── requirements-minimal.txt
├── .env.example
└── README.md
```

## 🔑 Key Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh access token

### Tasks
- `GET /api/v1/tasks` - List all tasks
- `POST /api/v1/tasks` - Create new task
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task
- `POST /api/v1/tasks/{id}/breakdown` - AI task breakdown

### Habits
- `GET /api/v1/habits` - List all habits
- `POST /api/v1/habits` - Create new habit
- `POST /api/v1/habits/{id}/complete` - Mark habit complete

### Calendar
- `GET /api/v1/calendar/events` - List events
- `POST /api/v1/calendar/events` - Create event
- `GET /api/v1/calendar/free-slots` - Find free time slots

### Emails
- `GET /api/v1/emails` - List emails
- `POST /api/v1/emails/sync` - Sync from Gmail
- `POST /api/v1/emails/{id}/analyze` - AI email analysis

### Notes
- `GET /api/v1/notes` - List notes
- `POST /api/v1/notes` - Create note
- `POST /api/v1/notes/search` - Search notes

### Chat
- `GET /api/v1/chat/sessions` - List chat sessions
- `POST /api/v1/chat/message` - Send message to AI

## 🤖 AI Features

### Task Agent
- Intelligent task breakdown
- Priority suggestions
- Deadline recommendations

### Email Agent
- Email summarization
- Category classification
- Reply suggestions
- Priority scoring

### Planner Agent
- Daily planning
- Schedule optimization
- Task prioritization

### Orchestrator
- Multi-agent coordination
- Context management
- Response synthesis

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- SQL injection prevention (SQLAlchemy ORM)
- Input validation (Pydantic)

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| SECRET_KEY | JWT secret key | Yes |
| OPENAI_API_KEY | OpenAI API key | Yes |
| CORS_ORIGINS | Allowed CORS origins | Yes |
| GOOGLE_CLIENT_ID | Google OAuth client ID | No |
| GOOGLE_CLIENT_SECRET | Google OAuth secret | No |

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t life-copilot-backend .

# Run container
docker run -p 8000:8000 --env-file .env life-copilot-backend
```

### Production

1. Set `DEBUG=False` in production
2. Use a production WSGI server (Gunicorn + Uvicorn)
3. Set up SSL/TLS certificates
4. Configure proper CORS origins
5. Use environment-specific secrets
6. Set up database migrations with Alembic

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

**Jino-X**

- GitHub: [@Jino-X](https://github.com/Jino-X)

## 🙏 Acknowledgments

- FastAPI for the amazing framework
- OpenAI for GPT-4 API
- LangChain for AI orchestration
- ChromaDB for vector storage

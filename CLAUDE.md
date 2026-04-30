# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based conversational AI application providing "digital twins" of different personas for educational consultation:
- **AI张老师**: Based on 张雪峰 style for college entrance exam and postgraduate application guidance
- **教员**: Based on Mao Zedong's personality and thinking patterns

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Main optimized application with auth (port 5002)
python app.py

# Fast version with strict timeout control (port 5001)
python app_fast.py

# Standalone auth version
python app_with_auth.py

# Start with dependency check
python start_app_with_auth.py

# Unified service - starts both Flask (:5002) and Node.js Word service (:3001)
./start_unified.sh
```

## Architecture

### Application Entry Points

- **app.py**: Main optimized application (port 5002) - includes auth, parallel API calls, caching, multiple personas, and Word service proxy
- **app_fast.py**: Fast version (port 5001) with strict 15s response timeout and performance monitoring
- **app_with_auth.py**: Standalone version with user login, registration, and chat history persistence

### Request Flow

1. User submits question via POST `/chat` (张老师) or `/pedu/chat` (教员)
2. **Parallel execution**: RAG search + session history fetch (using ThreadPoolExecutor)
3. LLM generates response using persona prompt + context (DeepSeek or Aliyun Application API)
4. Response returned with `answer`, `session_id`, `processing_time`
5. Caching applied at multiple levels (RAG, LLM, full response)
6. Chat history saved to database if user is authenticated

### Service Layer (`services/`)

- **rag_service.py**: Knowledge base search using Aliyun Responses API with vector stores
  - `search_knowledge()` - 张老师 persona knowledge base
  - `search_knowledge_j()` - 教员 persona knowledge base
- **llm_service.py** / **llm_service_improved.py**: LLM calls via DeepSeek API
  - `ask_llm()` - 张老师 persona
  - `ask_llm_j()` - 教员 persona (uses llm_service_jiao.py)
- **app_service.py**: Aliyun Application.call API wrapper
  - `call_application()` - Standard call
  - `call_application_with_context()` - With context/history
  - `call_pedu_application()` - 教员 application
- **session_service.py**: Session management using Redis with in-memory fallback
- **sms_service.py**: SMS verification code service (dev: prints to console)
- **tts_service.py**: Text-to-speech (currently disabled in main flow)
- **filter_service.py**: Question relevance filtering

### Utility Layer (`utils/`)

- **cache_improved.py**: Hybrid cache (Redis with memory fallback)
  - `get_cache()`, `set_cache()`, `clear_cache()`
  - Automatic fallback from Redis to in-memory cache
- **logger.py**: Centralized logging with rotation
- **performance.py**: Performance monitoring and timing decorators

### Prompt Templates (`promot/`)

- **promot.py** (`promot_z`): AI张老师 persona - humorous, direct, employment-focused
- **promot_jiaoyuan.py** (`promot_j`): 教员 persona - based on TENSEI architecture

### Configuration (`config.py`)

All sensitive values loaded from environment variables:
- `DEEPSEEK_API_KEY`, `DEEPSEEK_URL`
- `ALIYUN_API_KEY`, `ALIYUN_BASE_URL`
- `KNOWLEDGE_BASE_ID` (张老师), `KNOWLEDGE_BASE_ID_J` (教员)
- `ALIYUN_APP_ID`, `ALIYUN_APP_ID_J`
- `REDIS_URL`

### Database Models (`models.py`)

- **User**: id, username, password_hash, phone_number, email, full_name, created_at, last_login, is_active
- **UserSession**: session tracking with expiration (7 days), ip_address, user_agent
- **ChatHistory**: message storage linked to user_id and session_id
- **VerificationCode**: SMS verification codes with expiration tracking

### Authentication System (`auth.py`)

- **Password login**: `authenticate_user()`, `register_user()`
- **SMS login**: `login_by_phone()` - auto-registers new users
- **Session management**: `create_user_session()`, `get_user_session()`, `logout_user_session()`
- **Chat history**: `save_chat_message()`, `get_chat_history()`

## Key Routes

- `GET /` - Redirects to login if not authenticated, else home
- `GET /login`, `GET /register` - Auth pages
- `GET /cyborg` - Persona selection page (requires login)
- `GET /standard` - 张老师 interface (requires login)
- `GET /pedu` - 教员 interface (requires login)
- `GET /app` - Application ID interface (requires login)
- `POST /chat` - 张老师 chat endpoint
- `POST /pedu/chat` - 教员 chat endpoint
- `POST /app/chat` - Application ID chat endpoint with history support
- `POST /api/login`, `POST /api/register` - Auth APIs
- `POST /api/send-code`, `POST /api/phone-login` - SMS auth APIs
- `GET /api/user/info` - Current user info
- `GET /health` - Health check with service status
- `GET /performance` - Performance statistics

## Word Service Reverse Proxy

The app includes a reverse proxy to a Node.js Word document filling service:
- `GET/POST /word/*` - Proxied to `WORD_SERVICE_URL` (default: http://localhost:3001)
- `GET /word/health` - Check Word service availability
- Returns 503 with `word_service_down.html` if service is unavailable

## Environment Variables

Required in `.env` file:
```
DEEPSEEK_API_KEY=your_deepseek_key
ALIYUN_API_KEY=your_aliyun_key
ALIYUN_APP_ID=your_app_id
ALIYUN_APP_ID_J=your_jiaoyuan_app_id
KNOWLEDGE_BASE_ID=your_kb_id
KNOWLEDGE_BASE_ID_J=your_j_kb_id
FLASK_SECRET_KEY=your_secret_key
```

Optional:
```
WORD_SERVICE_URL=http://localhost:3001
REDIS_URL=redis://localhost:6379
PORT=5002
```

## Performance Tuning

In **app_fast.py**, adjust these constants:
- `MAX_RESPONSE_TIME` (default 15s) - Total allowed response time
- `RAG_TIMEOUT` (default 6s) - Knowledge base search timeout
- `LLM_TIMEOUT` (default 10s) - LLM generation timeout
- `CACHE_TTL` (default 300s) - Cache expiration

## Database Migration

The app uses SQLite by default (`app.db`). To migrate to MySQL:
1. Install `pymysql`: `pip install pymysql`
2. Modify `models.py` init_db function:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@localhost:3306/dbname'
   ```
3. Restart app to recreate tables

## Test Accounts

Auto-created on first run:
- **testuser / test123** - Regular user (phone: 13800138000)
- **admin / admin123** - Admin user (phone: 13900139000)

## SMS Verification (Development Mode)

In development mode, SMS codes are printed to console instead of being sent. Check terminal output for the verification code when using `/api/phone-login`.

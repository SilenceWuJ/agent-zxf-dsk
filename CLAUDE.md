# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based conversational AI application providing a "digital twin" of AI张老师, based on the style of 张雪峰, a famous Chinese education consultant specializing in college entrance exam and postgraduate exam application guidance.

## Dependencies

To set up the environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install flask requests openai
```

Core dependencies:
- Flask (web framework)
- requests (HTTP client)
- openai (for Aliyun API compatibility)
- wave (standard library - audio handling)

## Running the Application

```bash
source venv/bin/activate
python app_.py
```

The Flask server runs on `http://0.0.0.0:5000`

## Architecture

### Main Components

- **app.py**: Single Flask application file containing:
  - Flask route handlers (`/` and `/chat`)
  - `get_rag_response()`: Retrieves context from Aliyun knowledge base using Responses API
  - `call_deepseek_with_context()`: Calls DeepSeek API with retrieved context and system prompt
  - `text_to_speech()`: (commented out) Tencent Cloud TTS integration for voice cloning

- **main.html**: Frontend interface with simple chat UI that:
  - Sends POST requests to `/chat` endpoint
  - Displays text response
  - Plays audio response if available

### External APIs Used

1. **DeepSeek API** (`https://api.deepseek.com/chat/completions`):
   - Primary chat completion
   - Model: `deepseek-chat`

2. **Aliyun Responses API** (`https://dashscope.aliyuncs.com/compatible-mode/v1`):
   - RAG knowledge base retrieval
   - Uses OpenAI SDK compatibility mode
   - Model: `qwen3.5-plus`
   - Vector store ID: `7lef75e879`

3. **Tencent Cloud TRTC/TTS** (commented out):
   - Voice cloning and synthesis
   - Region: `ap-guangzhou`

### Request Flow

1. User submits question via HTML form → POST `/chat`
2. Aliyun RAG retrieves relevant context from knowledge base
3. DeepSeek generates response using system prompt + context
4. Response returned as JSON with `answer` field (audio currently disabled)

### System Prompt

The `SYSTEM_PROMPT` defines the persona as AI张老师:
- Humorous, direct, passionate speaking style
- Northeast dialect markers (e.g., "整", "老好了")
- Employment-focused advice for ordinary families
- Uses specific examples and comparisons
- Honest about uncertainty when knowledge base lacks info

## API Key Management

API keys are currently hardcoded in `app.py`:
- `DEEPSEEK_API_KEY`
- `ALIYUN_API_KEY`
- `ALIYUN_BASE_URL`
- `KNOWLEDGE_BASE_ID`

These should be moved to environment variables for production.

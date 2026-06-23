# LinguaFlow AI 🗣️🤖

![LinguaFlow AI](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11+-blue.svg) ![Next.js](https://img.shields.io/badge/Next.js-14-black) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg) ![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)

**LinguaFlow AI** is a complete web application designed for conversational language learning powered by AI. It features text and voice chat capabilities, document-based Retrieval-Augmented Generation (RAG), comprehensive analytics, and system auditing for tokens and latency.

## ✨ Features

- **Conversational AI**: Practice languages via text or voice.
- **Multi-Provider Support**: Seamlessly switch between local AI (Ollama) and cloud APIs (Google Gemini).
- **Advanced RAG System**: Upload documents, chunk text, and perform vector searches to ground AI responses in your custom context.
- **Admin Dashboard**: Manage settings, monitor system latency, track token usage, and adjust RAG confidence thresholds.
- **Robust Authentication**: Secure admin access with hashed master passwords and HTTP-only cookies, plus Google OAuth support for users.
- **Developer-Friendly**: Hot-reloading development scripts, Docker Compose for production-like environments, and robust logging.

## 🏗️ Tech Stack

> **📖 Want to dive deeper?** Check out our detailed [Architecture & Design Document](ARCHITECTURE.md) to learn about data flows, system components, and core strengths.

- **Frontend**: Next.js (React), TailwindCSS, TypeScript.
- **Backend**: Python, FastAPI, SQLAlchemy, LlamaIndex/LangChain concepts.
- **Database**: PostgreSQL with `pgvector` for vector embeddings.
- **Caching & Async**: Redis.
- **Connection Pooling**: PgBouncer.
- **Monitoring**: Prometheus (optional).
- **AI Models**: Local inference via Ollama (`llama3.2`, `nomic-embed-text`) or Google Gemini.
- **Infrastructure**: Docker, Docker Compose, Nginx.

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure it's running)
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.11+)
- [Ollama](https://ollama.com/) (Optional, but highly recommended for local, free AI inference)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/language_ai_app.git
cd language_ai_app
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```
*Note: The default settings in `.env.example` are pre-configured to work out-of-the-box with the local development scripts.*

### 3. Local Development (Fast Mode)

The easiest way to start developing is using our hybrid fast-mode script. It runs databases in Docker, but keeps the Frontend (Next.js) and Backend (FastAPI) running natively on your OS for instant hot-reloading.

**On Windows (PowerShell):**
```powershell
.\scripts\dev-fast.ps1
```

This script will automatically:
1. Create a Python `.venv` and install backend dependencies.
2. Install Node.js frontend dependencies.
3. Spin up Postgres and Redis in Docker.
4. Launch the FastAPI backend and Next.js frontend in separate windows.
5. Open your browser to `http://localhost:3000`.

**Useful Flags:**
- `.\scripts\dev-fast.ps1 -SkipPrometheus` : Run without Prometheus monitoring.
- `.\scripts\dev-fast.ps1 -NoInstall` : Skip dependency installation (faster startups).

### 4. Full Docker Environment (Production-like)

If you want to run the entire stack (including Nginx routing) inside Docker:

```powershell
.\scripts\dev-up.ps1
```
*(Or run `make up` if you have Make installed).*

Access the application:
- Web: `http://localhost`
- API Health: `http://localhost/api/v1/health`
- Swagger Docs: `http://localhost/docs`

---

## 🧠 AI Configuration (Ollama)

For the best free, private experience, we use **Ollama**.

1. Install Ollama on your host machine.
2. Pull the required models:
   ```powershell
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
3. Start the Ollama server:
   ```powershell
   ollama serve
   ```
*Note: Our scripts automatically detect Ollama and optimize it to use your NVIDIA GPU (CUDA) by disabling conflicting Vulkan fallback settings.*

If you prefer to use **Google Gemini**:
Update your `.env` file:
```env
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_LLM_MODEL=gemini-3.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

---

## 🗺️ Application Structure

- `/frontend` - Next.js application.
- `/backend` - FastAPI application.
- `/infra` - Nginx and database initialization scripts.
- `/scripts` - Automation scripts for Windows/Linux (`dev-fast`, `dev-up`, `rebuild`).
- `/docs` - Additional documentation.

## 🧹 Maintenance Commands

Clean up Docker space without losing your database volumes or Ollama models:
```powershell
.\scripts\clean-docker.ps1
```

Rebuild the Docker containers safely:
```powershell
.\scripts\rebuild.ps1
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

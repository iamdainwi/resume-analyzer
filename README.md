# Resume Analyzer

An AI-powered resume screening tool that evaluates candidates against job descriptions. Upload resumes, provide a job description, and get instant rankings with skill-match breakdowns.

Built with **FastAPI** (Python) on the backend and **Next.js** (TypeScript) on the frontend.

---

## Features

- **AI-Powered Scoring** — Uses an LLM (via Ollama) to evaluate resumes against job descriptions on a 0–100 scale
- **Keyword Fallback** — Automatic keyword-matching fallback when the LLM is unavailable
- **Batch Processing** — Upload up to 20 resumes at once with real-time progress tracking
- **Smart Name Extraction** — Multi-strategy name detection from resume text, email addresses, and common patterns
- **Candidate Ranking** — Results sorted by score with Excellent / Strong / Partial / Weak classifications
- **Skill Match Breakdown** — Visual keyword overlap between the JD and each resume
- **Drag & Drop Upload** — Supports PDF, DOC, and DOCX files

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3.10+, FastAPI, SQLAlchemy, Uvicorn |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| LLM      | Ollama (configurable model)         |
| Database | SQLite (default, configurable)      |
| Parsing  | pdfplumber (PDF), python-docx (DOCX) |

---

## Project Structure

```
resume-analyzer-main/
├── backend/
│   ├── app/
│   │   ├── __init__.py         # Package marker
│   │   ├── config.py           # Centralized environment-based configuration
│   │   ├── database.py         # SQLAlchemy engine, session factory, get_db dependency
│   │   ├── models.py           # Job and Candidate ORM models
│   │   ├── main.py             # FastAPI app, routes, middleware, lifespan
│   │   ├── llm_service.py      # LLM scoring + keyword fallback
│   │   ├── resume_parser.py    # PDF/DOCX text extraction + name detection
│   │   ├── job_service.py      # Background job processing logic
│   │   └── utils.py            # Timing decorator + performance logger
│   ├── .env.example            # Template for environment variables
│   └── requirements.txt        # Pinned Python dependencies
│
├── frontend/
│   ├── app/
│   │   ├── globals.css         # Design system (CSS variables, animations)
│   │   ├── layout.tsx          # Root layout with metadata
│   │   └── page.tsx            # Main UI — upload, progress, results
│   ├── package.json
│   └── next.config.ts
│
└── .gitignore
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Ollama** (optional — for AI scoring; falls back to keyword matching without it)

### 1. Clone the Repository

```bash
git clone https://github.com/iamdainwi/resume-analyzer-main.git
cd resume-analyzer-main
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv env
source env/bin/activate        # macOS / Linux
# env\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional — defaults work for local dev)
cp .env.example .env
# Edit .env to set OLLAMA_API_KEY, OLLAMA_HOST, etc.

# Start the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The UI will be available at `http://localhost:3000`.

### 4. Ollama Setup (Optional)

For AI-powered scoring instead of basic keyword matching:

```bash
# Install Ollama (macOS)
brew install ollama

# Start the Ollama server
ollama serve

# Pull a model (update OLLAMA_MODEL in .env to match)
ollama pull llama3
```

Then set these in `backend/.env`:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## API Endpoints

| Method | Endpoint              | Description                          |
|--------|-----------------------|--------------------------------------|
| GET    | `/`                   | Health check                         |
| POST   | `/start-job`          | Upload resumes + JD, start analysis  |
| GET    | `/job-status/{id}`    | Poll job progress and get results    |

### POST `/start-job`

**Content-Type:** `multipart/form-data`

| Field   | Type     | Description                    |
|---------|----------|--------------------------------|
| `jd`    | string   | Job description text           |
| `files` | file[]   | Resume files (PDF, DOC, DOCX)  |

**Response:**
```json
{
  "job_id": 1,
  "message": "Processing started",
  "total_files": 3
}
```

### GET `/job-status/{id}`

**Response:**
```json
{
  "status": "completed",
  "processed": 3,
  "total": 3,
  "candidates": [
    {
      "name": "Jane Smith",
      "score": 87.5,
      "classification": "Excellent",
      "summary": "Strong match with 5+ years of relevant experience..."
    }
  ]
}
```

---

## Configuration

All settings are configured via environment variables. See [`backend/.env.example`](backend/.env.example) for the full list:

| Variable           | Default                         | Description                          |
|--------------------|---------------------------------|--------------------------------------|
| `DATABASE_URL`     | `sqlite:///./hr.db`             | Database connection string           |
| `OLLAMA_HOST`      | `https://ollama.com`            | Ollama server URL                    |
| `OLLAMA_MODEL`     | `gpt-oss:120b`                  | LLM model name                       |
| `OLLAMA_API_KEY`   | _(empty)_                       | API key for Ollama                   |
| `CORS_ORIGINS`     | `http://localhost:3000,...`      | Comma-separated allowed origins      |
| `UPLOAD_DIR`       | `uploads`                       | Directory for temporary file uploads |
| `MAX_UPLOAD_FILES` | `20`                            | Max files per job                    |
| `LOG_LEVEL`        | `INFO`                          | Python logging level                 |

The frontend uses:

| Variable               | Default                    | Description        |
|------------------------|----------------------------|--------------------|
| `NEXT_PUBLIC_API_URL`  | `http://127.0.0.1:8000`   | Backend API URL    |

---

## How It Works

```
User uploads resumes + JD
        │
        ▼
   POST /start-job
        │
        ├── Save files to disk
        ├── Create Job record in DB
        └── Kick off background task
                │
                ▼
        For each resume file:
        ┌───────────────────────┐
        │ 1. Extract text (PDF/ │
        │    DOCX parser)       │
        │ 2. Extract name       │
        │    (multi-strategy)   │
        │ 3. Score via LLM      │
        │    (or keyword        │
        │    fallback)          │
        │ 4. Save Candidate     │
        │    record to DB       │
        │ 5. Update progress    │
        └───────────────────────┘
                │
                ▼
        Mark job as completed
        Clean up uploaded files
```

The frontend polls `GET /job-status/{id}` every 3 seconds to update the progress bar and display results as they come in.

---

## License

This project is for educational and personal use.

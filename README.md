
# Smart Resume Screener

A small FastAPI service to upload PDF resumes, extract text, parse basic resume fields (name, contact, skills, education, experience), store them in MongoDB, and optionally score resumes against a job description using Google Gemini (or a simple fallback heuristic).

This README explains the project layout, how to set up the development environment on Windows, how to run the server, available API endpoints, environment variables, common troubleshooting steps, and next steps you can take.

## Demo Video
Video link: [Google Drive Link](https://drive.google.com/file/d/1Y9avi00WaiYbgWqhuPOOtInhpUIb0UHA/view?usp=drive_link)


## Table of Contents

- Project structure
- Features
- Requirements
- Setup (Windows)
- Running the server
- API endpoints
- Environment variables
- Troubleshooting
- Development notes
- License / author

## Project structure

Top-level files/folders (relevant):

- `backend/` - Python FastAPI backend
  - `requirements.txt` - pinned dependencies
  - `app/` - backend application code
    - `main.py` - FastAPI app and endpoints
    - `pdf_utils.py` - PDF text extraction (PyMuPDF / fitz)
    - `parser.py` - simple resume parsing using spaCy + heuristics
    - `db.py` - MongoDB (motor) client and helpers
    - `gemini_client.py` - optional LLM scoring integration (Google Gemini)
    - `models.py` - Pydantic models used by the app

## Features

- Upload PDF resumes and extract full text
- Parse name, email, phone, skills, education, and experience lines
- Persist resumes and parsed output to MongoDB
- Trigger background scoring against a job description using either:
  - Google Gemini API (if `GEMINI_API_KEY` provided) or
  - A simple fallback heuristic when no key is configured

## Requirements

- Python 3.10+ (the repo was developed for Python 3.11/3.12 but 3.10+ should work)
- MongoDB (local or remote)
- Windows (instructions below are Windows-first)

Python dependencies are in `backend/requirements.txt`.

## Setup (Windows)

1. Open Command Prompt (cmd.exe) or PowerShell. The examples here use cmd.exe.

2. Create and activate a virtual environment (recommended):

```cmd
cd /d D:\unthinkable_solutions\smart-resume-screener\backend
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```cmd
pip install -r requirements.txt
```

4. Install spaCy language model (required by `parser.py`):

```cmd
python -m spacy download en_core_web_sm
```

5. Configure environment variables. Create a `.env` file in `backend/` with values you need. Example `.env`:

```
# MongoDB connection (default used if not set)
MONGODB_URI=mongodb://localhost:27017
MONGO_DB=resume_screener

# Optional: Google Gemini API key
GEMINI_API_KEY=
```

6. Ensure MongoDB is running locally or set `MONGODB_URI` to a reachable MongoDB instance.

## Running the server

From `backend/` in Command Prompt (cmd.exe):

```cmd
cd /d D:\unthinkable_solutions\smart-resume-screener\backend
python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

Notes:
- In PowerShell you can use a semicolon to separate commands (or run the `cd` and `uvicorn` commands separately). Avoid using `&&` in PowerShell.
- If your environment uses a different Python interpreter, adjust the commands accordingly.

Once running, visit http://127.0.0.1:8000/docs for the automatic Swagger UI.

## API endpoints

- POST /upload-resume
  - Accepts a `multipart/form-data` file upload (`file` field) — only `.pdf` supported.
  - Response: stored document id and parsed fields.

- POST /score/{resume_id}
  - Body params (form or query): `job_description` string. This endpoint enqueues a background scoring job (uses Gemini if configured, otherwise fallback heuristic).
  - Response: immediate acknowledgement that scoring started.

- GET /resume/{resume_id}
  - Returns stored resume doc including `parsed` and `scores` array.

## Environment variables

- `MONGODB_URI` (optional) — MongoDB connection string. Default: `mongodb://localhost:27017`.
- `MONGO_DB` (optional) — database name. Default: `resume_screener`.
- `GEMINI_API_KEY` (optional) — if set, the app will call Google Gemini to score resumes.

Put these in `backend/.env` or set them in your environment.

## Troubleshooting

- The shell error I observed when starting the app was: "The token '&&' is not a valid statement separator in this version." This means the one-liner used was parsed by PowerShell and used `&&`. Use cmd.exe or separate the commands with `;` in PowerShell, or run them separately.

- ModuleNotFoundError for packages: run `pip install -r requirements.txt` inside your activated venv.

- spaCy model not found: run `python -m spacy download en_core_web_sm`.

- MongoDB connection refused: ensure MongoDB is running locally or set `MONGODB_URI` to a valid connection string (and set any required auth credentials).

- PyMuPDF / fitz errors on Windows: ensure you installed the `pymupdf` wheel compatible with your Python version. Reinstall with pip if necessary.

- If Gemini parsing fails: the code attempts to parse JSON out of the model output. If Gemini returns unexpected text, the code falls back to a safe error response; check stdout for "Error parsing Gemini response:" messages.

If you run into an error you can't resolve, paste the full traceback (the terminal output) here and I'll help debug further.

## Development notes

- The parser is intentionally simple (spaCy for NER + regex heuristics). Expand `BASE_SKILLS` or integrate an external skills ontology for better results.
- The scoring is asynchronous and stores results in `resumes.scores` as a list of `ScoreResult` items.

## Next steps / improvements

- Add tests for parsing and PDF extraction.
- Improve skill extraction with a curated skills database and fuzzy matching.
- Add authentication and an admin UI for scoring and results.
- Add Dockerfile and docker-compose for quick local setup (Mongo + app).

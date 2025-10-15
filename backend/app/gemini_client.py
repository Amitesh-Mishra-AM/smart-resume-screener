import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINT = os.getenv(
    "GEMINI_API_ENDPOINT",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
)

# New prompt for resume parsing
PARSE_PROMPT_TEMPLATE = """
You are an expert resume parser. Extract the following information from the resume text in STRUCTURED JSON format:

{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "skills": ["list of technical skills", "programming languages", "tools"],
  "education": [
    {
      "degree": "degree name",
      "institution": "institution name", 
      "year": "graduation year"
    }
  ],
  "experience": [
    {
      "title": "job title",
      "company": "company name",
      "from_date": "start date",
      "to_date": "end date"
    }
  ],
  "total_experience_years": "total years of experience"
}

Rules:
- Extract ALL technical skills mentioned, don't limit to common ones
- For experience dates, use the format you find (MM/YYYY, Month YYYY, etc.)
- Calculate total_experience_years by summing all experience periods
- Return only valid JSON, no other text

Resume Text:
{resume_text}
"""

# Existing scoring prompt (keep this)
SCORE_PROMPT_TEMPLATE = """
You are an expert AI recruiter. Compare the candidate's resume and the given job description.
Evaluate based on **skills, education, experience, and project relevance**.

Return a **strict JSON** in this format:
{
  "score": number (0-100),
  "justification": ["short bullet points"],
  "matched_skills": ["skills or keywords found in both"],
  "missing_skills": ["skills missing from resume but present in job description"],
  "evidence": ["phrases from resume supporting the match"]
}

Base your score mainly on **semantic similarity**, not word count.

Resume Data:
{parsed_resume_json}

Job Description:
{job_description}
"""

async def parse_resume_with_gemini(text: str) -> dict:
    """Parse resume text using Gemini AI"""
    if not GEMINI_API_KEY:
        raise Exception("Gemini API key not configured for parsing")
    
    prompt = PARSE_PROMPT_TEMPLATE.format(resume_text=text)
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # FIX: Use params instead of appending to URL to avoid duplicate ?key=
            resp = await client.post(
                GEMINI_ENDPOINT,
                headers=headers,
                json=payload,
                params={"key": GEMINI_API_KEY}  # This is the fix
            )
            resp.raise_for_status()
            data = resp.json()

        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Clean the response - remove markdown code blocks if present
        text_output = text_output.replace("```json", "").replace("```", "").strip()
        
        try:
            parsed = json.loads(text_output)
            # Validate required fields
            parsed.setdefault("skills", [])
            parsed.setdefault("education", [])
            parsed.setdefault("experience", [])
            return parsed
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response as JSON: {text_output}")
            raise Exception(f"Gemini returned invalid JSON: {str(e)}")

    except Exception as e:
        print(f"Gemini parsing error: {e}")
        raise

async def score_resume_with_gemini(parsed_resume: dict, job_description: str) -> dict:
    """Sends parsed resume + job description to Gemini API and returns a structured score."""
    if not GEMINI_API_KEY:
        # Fallback logic (keep existing)
        skills = set([s.lower() for s in parsed_resume.get("skills", [])])
        jd = job_description.lower().split()
        matched = [s for s in skills if s in jd]
        score = int(len(matched) / (len(skills) or 1) * 100)
        return {
            "score": score,
            "justification": ["Fallback score computed from keyword overlap (Gemini not configured)."],
            "matched_skills": matched,
            "missing_skills": list(skills - set(matched)),
            "evidence": [],
            "raw_llm_response": None
        }

    prompt = SCORE_PROMPT_TEMPLATE.format(
        parsed_resume_json=json.dumps(parsed_resume, indent=2),
        job_description=job_description
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # FIX: Use params instead of appending to URL
            resp = await client.post(
                GEMINI_ENDPOINT,
                headers=headers,
                json=payload,
                params={"key": GEMINI_API_KEY}  # This is the fix
            )
            resp.raise_for_status()
            data = resp.json()

        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        try:
            parsed = json.loads(text_output)
        except Exception:
            parsed = {
                "score": 0,
                "justification": ["Invalid Gemini response format. Raw text received instead of JSON."],
                "matched_skills": [],
                "missing_skills": [],
                "evidence": [],
                "raw_text": text_output
            }

        for key in ["score", "justification", "matched_skills", "missing_skills", "evidence"]:
            parsed.setdefault(key, [] if key != "score" else 0)

        parsed["raw_llm_response"] = data
        return parsed

    except Exception as e:
        jd_words = job_description.lower().split()
        resume_text = json.dumps(parsed_resume).lower()
        matched = [w for w in jd_words if w in resume_text]
        missing = [w for w in jd_words if w not in resume_text]
        score = round(len(matched) / (len(jd_words) or 1) * 100, 2)

        return {
            "score": score,
            "justification": [f"Gemini request failed ({str(e)}). Used fallback keyword match scoring."],
            "matched_skills": matched,
            "missing_skills": missing,
            "evidence": [],
            "raw_llm_response": None
        }
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

PROMPT_TEMPLATE = """
You are an AI recruiter. Compare the given resume with the job description and
evaluate how well the resume matches the job requirements.

Return *only strict JSON* in this format:
{
  "score": number (0-100),
  "justification": [list of short reasons for the score],
  "matched_skills": [list of overlapping skills or keywords],
  "missing_skills": [list of key skills missing from the resume],
  "evidence": [list of resume phrases that support the match]
}

Resume Data:
{parsed_resume_json}

Job Description:
{job_description}
"""

async def score_resume_with_gemini(parsed_resume: dict, job_description: str) -> dict:
    """
    Sends parsed resume + job description to Gemini API and returns a structured score.
    Falls back to keyword-based scoring if Gemini fails or key not found.
    """

    # 🧩 Fallback scoring if no key is present
    if not GEMINI_API_KEY:
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

    # 🧠 Build the prompt
    prompt = PROMPT_TEMPLATE.format(
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

    # ⚙️ Send request
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        # 🧩 Extract and parse Gemini output
        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        try:
            parsed = json.loads(text_output)
        except Exception:
            # fallback if Gemini gives text not in JSON
            parsed = {
                "score": 0,
                "justification": ["Invalid Gemini response format. Raw text received instead of JSON."],
                "matched_skills": [],
                "missing_skills": [],
                "evidence": [],
                "raw_text": text_output
            }

        # ensure all required fields exist
        for key in ["score", "justification", "matched_skills", "missing_skills", "evidence"]:
            parsed.setdefault(key, [] if key != "score" else 0)

        parsed["raw_llm_response"] = data
        return parsed

    except Exception as e:
        # 🔥 Fallback heuristic if Gemini API call fails
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

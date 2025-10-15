import os
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from app.pdf_utils import extract_text_from_pdf_bytes
from app.parser import parse_resume_text
from app.db import get_collection
from app.models import ResumeDocument, ScoreResult
from app.gemini_client import score_resume_with_gemini
from dotenv import load_dotenv
from bson import ObjectId
import json

load_dotenv()

app = FastAPI(title="Smart Resume Screener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

resumes_col = get_collection("resumes")

# @app.post("/upload-resume")
# async def upload_resume(file: UploadFile = File(...)):
#     if not file.filename.lower().endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="Only PDF uploads accepted for now.")
#     content = await file.read()
#     text = extract_text_from_pdf_bytes(content)
#     parsed = parse_resume_text(text)
#     doc = {
#         "filename": file.filename,
#         "text": text,
#         "parsed": parsed,
#         "scores": []
#     }
#     res = await resumes_col.insert_one(doc)
#     return {"id": str(res.inserted_id), "parsed": parsed}

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), job_description: str = Form(...)):
    """Upload resume and job description together."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads accepted.")

    content = await file.read()

    try:
        text = extract_text_from_pdf_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {e}")

    parsed = parse_resume_text(text)
    doc = {
        "filename": file.filename,
        "text": text,
        "parsed": parsed,
        "scores": []
    }

    result = await resumes_col.insert_one(doc)
    resume_id = str(result.inserted_id)

    # Try Gemini scoring
    try:
        gemini_response = await score_resume_with_gemini(parsed, job_description)

        # Normalize Gemini response
        score_result = {
            "score": gemini_response.get("score") or 0,
            "matched_skills": gemini_response.get("matched_skills", []),
            "missing_skills": gemini_response.get("missing_skills", []),
            "justification": gemini_response.get("justification", []),
            "evidence": gemini_response.get("evidence", []),
            "raw_llm_response": gemini_response
        }

    except Exception as e:
        # fallback scoring if Gemini fails
        jd_lower = job_description.lower()
        resume_lower = text.lower()
        matched = [word for word in jd_lower.split() if word in resume_lower]
        missing = [word for word in jd_lower.split() if word not in resume_lower]
        score_val = round(len(matched) / len(jd_lower.split()) * 100, 2)
        score_result = {
            "score": score_val,
            "matched_skills": matched,
            "missing_skills": missing,
            "justification": [f"Matched {len(matched)} / {len(jd_lower.split())} keywords."],
            "evidence": [],
            "error": f"Gemini scoring failed: {str(e)}"
        }

    await resumes_col.update_one(
        {"_id": ObjectId(resume_id)},
        {"$push": {"scores": score_result}}
    )

    return {"id": resume_id, "parsed": parsed, "score_result": score_result}

@app.post("/score/{resume_id}")
async def score_resume(resume_id: str, job_description: str, background_tasks: BackgroundTasks):
    # find resume
    doc = await resumes_col.find_one({"_id": ObjectId(resume_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    parsed = doc.get("parsed")
    # call Gemini in background to not block
    async def _do_score(rid, parsed_resume, job_desc):
        try:
            llm_resp = await score_resume_with_gemini(parsed_resume, job_desc)
            score_result = ScoreResult(
                score=llm_resp.get("score", 0),
                justification=llm_resp.get("justification", []),
                matched_skills=llm_resp.get("matched_skills", []),
                missing_skills=llm_resp.get("missing_skills", []),
                evidence=llm_resp.get("evidence", []),
                raw_llm_response=llm_resp.get("raw_llm_response", llm_resp)
            )
            await resumes_col.update_one(
                {"_id": ObjectId(rid)},
                {"$push": {"scores": score_result.dict()}}
            )
        except Exception as e:
            # log error
            print("LLM scoring error:", e)
    background_tasks.add_task(_do_score, resume_id, parsed, job_description)
    return {"status": "scoring_started", "resume_id": resume_id}

@app.get("/resume/{resume_id}")
async def get_resume(resume_id: str):
    doc = await resumes_col.find_one({"_id": ObjectId(resume_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    doc["_id"] = str(doc["_id"])
    return doc

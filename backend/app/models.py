
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
from datetime import datetime

class ParsedExperience(BaseModel):
    title: Optional[str]
    company: Optional[str]
    from_date: Optional[str]
    to_date: Optional[str]

class ParsedEducation(BaseModel):
    degree: Optional[str]
    institution: Optional[str]
    year: Optional[str]

class ParsedResume(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    skills: List[str] = []
    education: List[ParsedEducation] = []
    experience: List[ParsedExperience] = []
    total_experience_years: Optional[float] = None

class ScoreResult(BaseModel):
    score: float
    justification: List[str]
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    evidence: List[str] = []
    raw_llm_response: Optional[Any] = None

class ResumeDocument(BaseModel):
    filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    text: str
    parsed: ParsedResume
    scores: List[ScoreResult] = []

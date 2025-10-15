import re
from typing import List
import spacy
from rapidfuzz import process, fuzz

nlp = spacy.load("en_core_web_sm")

# minimal curated skills list; expand as needed
BASE_SKILLS = [
    "python", "fastapi", "flask", "django", "nlp", "machine learning",
    "pytorch", "tensorflow", "scikit-learn", "sql", "mongodb", "docker", "aws",
    "keras", "linux", "git", "javascript", "react"
]

def extract_contact_info(text: str):
    email = None
    phone = None
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        email = email_match.group(0)
    phone_match = re.search(r'(\+?\d{1,3}[\s-]?)?(\d{10}|\d{3}[\s-]\d{3}[\s-]\d{4})', text)
    if phone_match:
        phone = "".join(phone_match.groups()[:2]).strip() if phone_match.groups() else phone_match.group(0)
    return email, phone

def extract_name(text: str):
    # simple heuristic: first PERSON entity found near top of document
    doc = nlp(text[:1000])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    # fallback: first line
    first_line = text.strip().splitlines()[0]
    if len(first_line.split()) <= 4:
        return first_line.strip()
    return None

def extract_education(text: str):
    edu_patterns = ["Bachelor", "B\\.Tech", "BTech", "Bachelors", "Master", "M\\.Tech", "MTech", "MBA", "PhD"]
    educations = []
    for line in text.splitlines():
        for p in edu_patterns:
            if re.search(p, line, re.IGNORECASE):
                educations.append({"degree": line.strip(), "institution": None, "year": None})
                break
    return educations

def extract_experience(text: str):
    # naive capture of lines with 'Engineer', 'Intern', 'Manager', etc.
    exp_lines = []
    for line in text.splitlines():
        if re.search(r"\b(Engineer|Developer|Intern|Manager|Scientist|Analyst|Lead)\b", line, re.IGNORECASE):
            exp_lines.append({"title": line.strip(), "company": None, "from_date": None, "to_date": None})
    return exp_lines

def extract_skills(text: str, top_k=10) -> List[str]:
    candidate = []
    lowered = text.lower()
    # simple search + fuzzy match for base skills
    for s in BASE_SKILLS:
        if s in lowered:
            candidate.append(s)
    # also fuzzy search for other candidate words (optional)
    # return unique
    return list(dict.fromkeys(candidate))[:top_k]

def parse_resume_text(text: str):
    name = extract_name(text)
    email, phone = extract_contact_info(text)
    education = extract_education(text)
    experience = extract_experience(text)
    skills = extract_skills(text)
    parsed = {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "education": education,
        "experience": experience,
        "total_experience_years": None
    }
    return parsed

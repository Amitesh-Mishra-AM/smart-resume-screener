import re
from typing import List, Dict
import spacy
from rapidfuzz import fuzz
from .gemini_client import parse_resume_with_gemini

nlp = spacy.load("en_core_web_sm")

BASE_SKILLS = [
    "python", "fastapi", "flask", "django", "nlp", "machine learning",
    "pytorch", "tensorflow", "scikit-learn", "sql", "mongodb", "docker", "aws",
    "keras", "linux", "git", "javascript", "react", "java", "c++", "c#", "html",
    "css", "typescript", "node.js", "vue", "angular", "spark", "hadoop"
]

def extract_email(text: str) -> str:
    matches = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return matches[0] if matches else None

def extract_phone(text: str) -> str:
    matches = re.findall(r"(\+?\d{1,3}[\s-]?)?(\d{10}|\d{3}[\s-]\d{3}[\s-]\d{4})", text)
    if matches:
        phone = "".join(matches[0])
        return phone.strip()
    return None

def extract_name(text: str) -> str:
    doc = nlp(text[:1000])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            if len(name.split()) <= 4:  
                return name
    for line in text.splitlines():
        line = line.strip()
        if line and not re.search(r"[\d@]", line) and len(line.split()) <= 4:
            return line
    return None

async def parse_resume_text(text: str) -> Dict:
    """Parse resume text using Gemini AI with fallback to rule-based parsing"""
    
    # Try Gemini parsing first
    try:
        print("🔄 Attempting to parse resume with Gemini...")
        parsed = await parse_resume_with_gemini(text)
        print("✅ Successfully parsed resume with Gemini")
        
        # Ensure all required fields are present
        parsed.setdefault("name", extract_name(text))
        parsed.setdefault("email", extract_email(text))
        parsed.setdefault("phone", extract_phone(text))
        parsed.setdefault("skills", [])
        parsed.setdefault("education", [])
        parsed.setdefault("experience", [])
        parsed.setdefault("total_experience_years", None)
        
        return parsed
        
    except Exception as e:
        print(f"❌ Gemini parsing failed, falling back to rule-based parser: {e}")
        return await fallback_parse_resume_text(text)

async def fallback_parse_resume_text(text: str) -> Dict:
    """Fallback rule-based parser when Gemini fails"""
    EDU_PATTERNS = [
        r"(Bachelor|B\.Tech|BTech|BSc|BA)", 
        r"(Master|M\.Tech|MTech|MSc|MA|MBA)", 
        r"(PhD|Doctorate)"
    ]

    EXP_KEYWORDS = r"\b(Engineer|Developer|Intern|Manager|Scientist|Analyst|Lead|Consultant|Specialist)\b"

    def extract_education(text: str) -> List[Dict]:
        education = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for pattern in EDU_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    degree = line.strip()
                    institution = lines[i + 1].strip() if i + 1 < len(lines) else None
                    year_match = re.search(r"(20\d{2}|19\d{2})", line)
                    year = year_match.group(0) if year_match else None
                    education.append({"degree": degree, "institution": institution, "year": year})
                    break
        return education

    def extract_experience(text: str) -> List[Dict]:
        experience = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(EXP_KEYWORDS, line, re.IGNORECASE):
                title = line.strip()
                company = lines[i + 1].strip() if i + 1 < len(lines) else None
                from_date, to_date = None, None
                date_match = re.findall(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}", line)
                if len(date_match) >= 1:
                    from_date = date_match[0]
                    if len(date_match) >= 2:
                        to_date = date_match[1]
                experience.append({"title": title, "company": company, "from_date": from_date, "to_date": to_date})
        return experience

    def extract_skills(text: str, top_k=15) -> List[str]:
        text_lower = text.lower()
        found = set()
        for skill in BASE_SKILLS:
            if skill.lower() in text_lower:
                found.add(skill)
            else:
                for word in text_lower.split():
                    if fuzz.ratio(skill.lower(), word) > 85:
                        found.add(skill)
        return list(found)[:top_k]

    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)
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

    print("---- DEBUG FALLBACK RESUME PARSER ----")
    print("Name:", name)
    print("Email:", email)
    print("Phone:", phone)
    print("Skills:", skills)
    print("Education:", education[:2])
    print("Experience:", experience[:2])
    print("-----------------------------")

    return parsed
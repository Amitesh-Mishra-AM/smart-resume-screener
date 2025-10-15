import streamlit as st
import requests
import json

# FastAPI backend URL
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart Resume Screener", layout="wide")

st.title("📄 Smart Resume Screener")
st.markdown("### Upload your resume and get an instant AI-based screening score!")

# File uploader
uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])

# Job description
job_description = st.text_area("Paste the Job Description here")

if uploaded_file and job_description:
    if st.button("Analyze Resume"):
        with st.spinner("Analyzing your resume... Please wait ⏳"):
            # Send file and job description to backend
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            data = {"job_description": job_description}

            try:
                response = requests.post(
                    f"{BACKEND_URL}/upload-resume",
                    files=files,
                    data=data,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Resume analyzed successfully!")
                    
                    # Display parsed data
                    st.subheader("📊 Parsed Resume Data")
                    st.json(result.get("parsed_resume", {}))

                    # Display score
                    st.subheader("🎯 Screening Score")
                    score = result.get("score", None)
                    if score:
                        st.metric(label="AI Match Score", value=f"{score} / 100")
                    else:
                        st.info("Score not available — check backend scoring logic.")
                else:
                    st.error(f"❌ Backend error: {response.text}")

            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.info("Please upload a resume and enter a job description to begin.")

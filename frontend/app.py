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

                    parsed = result.get("parsed", {})
                    st.subheader("📊 Parsed Resume Data")
                    if parsed:
                        st.json(parsed)
                    else:
                        st.warning("Parsed data not available — check backend response.")

                    score_data = result.get("score_result", {})
                    st.subheader("🎯 Screening Score")

                    if "score" in score_data:
                        st.write(f"**Score:** {score_data['score']} / 100")
                    else:
                        st.warning("Score not available — check backend scoring logic.")

                    if score_data.get("justification"):
                        st.write("**Justification:**")
                        for j in score_data["justification"]:
                            st.write(f"- {j}")
                    if score_data.get("matched_skills"):
                        st.write("**✅ Matched Skills:**", ", ".join(score_data["matched_skills"]))

                    if score_data.get("missing_skills"):
                        st.write("**⚠️ Missing Skills:**", ", ".join(score_data["missing_skills"]))

                else:
                    st.error(f"❌ Backend error: {response.text}")

            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.info("Please upload a resume and enter a job description to begin.")

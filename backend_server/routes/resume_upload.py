from fastapi import APIRouter, File, UploadFile, Request, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from services.db_client import supabase
import tempfile
import os
import re
import time
import json

router = APIRouter(prefix="/resume", tags=["Resume Upload"])

# ------------------ GEMINI SETUP ------------------
api_key = os.getenv("RESUME_API")
print("API KEY:", api_key)

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    google_api_key=api_key
)

# ------------------ CLEAN TEXT ------------------
def clean_resume_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

# ------------------ ROUTE ------------------
@router.post("/")
def upload_resume(request: Request, file: UploadFile = File(...)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    start_time = time.time()

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        # Load PDF
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        full_text = "\n".join(page.page_content for page in pages)

        cleaned_text = clean_resume_text(full_text)

        # ------------------ GEMINI CALL ------------------
        response = model.invoke(
            f"""
            Analyze this resume and return ONLY JSON:

            {{
              "analysis": "short evaluation of resume",
              "resume_score": number (0-100),
              "skill_analysis": "what to improve",
              "suggested_projects": ["project1", "project2"]
            }}

            Resume:
            {cleaned_text}
            """
        )

        print("RAW RESPONSE:", response.content)

        # ------------------ CLEAN JSON ------------------
        raw_text = response.content.strip()
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        print("CLEANED RESPONSE:", raw_text)

        # ------------------ PARSE JSON ------------------
        try:
            json_response = json.loads(raw_text)
        except Exception as e:
            print("JSON PARSE ERROR:", e)
            json_response = {}

        # ------------------ SAFE FALLBACK ------------------
        ai_analysis = {
            "analysis": json_response.get("analysis") or "Your resume needs improvement in clarity and structure.",
            "resume_score": json_response.get("resume_score") or 60,
            "skill_analysis": json_response.get("skill_analysis") or "Improve core technical and problem-solving skills.",
            "suggested_projects": json_response.get("suggested_projects") or [
                "Build a full-stack web app",
                "Create an AI-based project"
            ]
        }

        # ------------------ SAVE TO DB ------------------
        try:
            supabase.rpc(
                "upsert_full_resume",
                {
                    "p_user_id": int(user_id),
                    "data": ai_analysis
                }
            ).execute()
        except Exception as db_error:
            print("DB ERROR:", db_error)

        end_time = time.time()

        return {
            "message": "Resume processed successfully",
            "data": ai_analysis,
            "processing_time": round(end_time - start_time, 2)
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {"error": str(e)}

    finally:
        os.remove(tmp_path)
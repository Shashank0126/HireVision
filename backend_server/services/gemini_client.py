import time
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import HTTPException

def create_gemini_model(model_name="gemini-2.5-flash", temperature=1.0, api_key=None):
    """Create Gemini model with error handling"""
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, api_key=api_key)

def invoke_with_retry(model, messages, max_retries=3, retry_delay=30):
    """Invoke model with retry logic for quota exceeded errors"""
    for attempt in range(max_retries):
        try:
            return model.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            if ("resource_exhausted" in error_str or "429" in error_str or "quota" in error_str):
                if attempt < max_retries - 1:
                    # Extract retry delay from error if available
                    delay = retry_delay
                    if "retry in" in str(e):
                        try:
                            delay_str = str(e).split("retry in")[1].split("s")[0].strip()
                            delay = float(delay_str) + 1  # Add 1 second buffer
                        except:
                            pass
                    print(f"Quota exceeded, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise HTTPException(
                        status_code=429,
                        detail="AI service quota exceeded. Please upgrade your plan at https://ai.google.dev/ or try again tomorrow."
                    )
            else:
                # Re-raise non-quota errors
                raise
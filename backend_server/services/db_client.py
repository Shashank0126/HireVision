import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError("supabase_url is required")

if not SUPABASE_KEY:
    raise ValueError("supabase_key is required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
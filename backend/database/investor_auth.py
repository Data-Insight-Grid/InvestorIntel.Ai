import os
import re
import bcrypt
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env vars
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 🔐 Hash password
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# ✅ Username pattern validator
def is_valid_username(username: str) -> bool:
    return re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]*$", username) is not None

# ✅ Signup function
def signup_investor(first_name: str, last_name: str, username: str, email: str, password: str) -> dict:
    # ❌ Check for missing fields
    if not all([first_name, last_name, username, email, password]):
        return {"status": "error", "message": "All fields are required."}

    # ❌ Check for valid username pattern
    if not is_valid_username(username):
        return {"status": "error", "message": "Username must start with a letter and only contain letters, numbers, or underscores."}

    # ❌ Check if email already exists
    email_check = supabase.table("InvestorLogin").select("email").eq("email", email).execute()
    if email_check.data:
        return {"status": "error", "message": "Email already registered."}

    # ❌ Check if username already exists
    username_check = supabase.table("InvestorLogin").select("username").eq("username", username).execute()
    if username_check.data:
        return {"status": "error", "message": "Username already taken."}

    hashed_pw = hash_password(password)
    new_user = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "email": email,
        "password_hash": hashed_pw
    }

    supabase.table("InvestorLogin").insert(new_user).execute()
    return { "status": "success", "username": username }


# ✅ Login function
def login_investor(username: str, password: str) -> dict:
    # ❌ Check for missing fields
    if not username or not password:
        return {"status": "error", "message": "Email and password are required."}

    result = supabase.table("InvestorLogin").select("*").eq("username", username).execute()

    if not result.data:
        return {"status": "error", "message": "User not found."}

    user = result.data[0]
    if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        return {
            "status": "success",
            "username": user.get("username")
        }
    else:
        return {"status": "error", "message": "Incorrect password."}


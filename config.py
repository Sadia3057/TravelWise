import os
from dotenv import load_dotenv

load_dotenv()   # reads the .env file automatically

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
NVIDIA_API_KEY      = os.getenv("NVIDIA_API_KEY", "")
SMTP_EMAIL          = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD       = os.getenv("SMTP_PASSWORD", "")
SECRET_KEY          = os.getenv("SECRET_KEY", "travelwise-secret-2025")
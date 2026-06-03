import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-999')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/resume_analyzer')
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    
    # AI Config
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'groq').lower()
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import os
from dotenv import load_dotenv


load_dotenv(override=True, verbose=True)

# n8n API configuration
N8N_BASE_URL = os.getenv("N8N_API_URL", "http://localhost:5678")
N8N_API_URL = f"{N8N_BASE_URL}/api/v1"
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
import os
from dotenv import load_dotenv

# Load environment variables from the "конфіг" file
load_dotenv()

# Access environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
TOKEN = os.getenv('TOKEN')
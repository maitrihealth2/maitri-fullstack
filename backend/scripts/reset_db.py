import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database.models import reset_db

if __name__ == "__main__":
    print("Initializing Database Reset...")
    reset_db()

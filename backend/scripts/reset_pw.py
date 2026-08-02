import os
from sqlalchemy.orm import Session
from core.database.models import SessionLocal, User
from security.authentication.service import hash_password

def reset_password():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test@test.com").first()

    if user:
        user.hashed_password = hash_password("password123")
        db.commit()
        print("Password reset successfully to 'password123'.")
    else:
        print("User test@test.com not found in the database.")
    db.close()

if __name__ == "__main__":
    reset_password()

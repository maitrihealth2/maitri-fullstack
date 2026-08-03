from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.exceptions import DomainError, UnauthorizedError, ResourceNotFoundError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from core.database.models import get_db, User
from security.authentication.service import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer()

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    preferred_language: str = Field(default="en-IN", max_length=10)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

class GoogleLoginRequest(BaseModel):
    idToken: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    roles: list[str] = []


def parse_roles(roles_value: str | list[str] | None) -> list[str]:
    if roles_value is None:
        return []
    if isinstance(roles_value, list):
        return [r.strip() for r in roles_value if r.strip()]
    return [r.strip() for r in roles_value.split(",") if r.strip()]


def RoleChecker(allowed_roles: list[str]):
    def checker(current_user: User = Depends(get_current_user)):
        user_roles = parse_roles(getattr(current_user, "roles", "user"))
        if "admin" in user_roles:
            return current_user
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions for this operation.")
        return current_user
    return checker


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_token(credentials.credentials, expected_type="access")
    if not payload:
        raise UnauthorizedError("Invalid or expired token")
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise UnauthorizedError("User not found")
    return user

def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,     # Must be HTTPS in prod
        samesite="strict",
        max_age=7 * 24 * 60 * 60
    )

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise DomainError("Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise DomainError("Username already taken")
    
    from providers.firebase.firebase_rest import firebase_client
    await firebase_client.register(req.email, req.password)
    
    user = User(
        username=req.username, email=req.email,
        hashed_password="firebase_managed",
        preferred_language=req.preferred_language,
        roles="user"
    )
    db.add(user); db.commit(); db.refresh(user)
    
    token_payload = {"user_id": user.id, "username": user.username, "roles": parse_roles(user.roles)}
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(
        access_token=token,
        username=user.username,
        roles=parse_roles(user.roles),
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    from providers.firebase.firebase_rest import firebase_client
    await firebase_client.login(req.email, req.password)
    
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise UnauthorizedError("Invalid email or password")
        
    token_payload = {"user_id": user.id, "username": user.username, "roles": parse_roles(user.roles)}
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(
        access_token=token,
        username=user.username,
        roles=parse_roles(user.roles),
    )

@router.post("/google", response_model=TokenResponse)
async def google_login(req: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)):
    from providers.firebase.firebase_rest import FIREBASE_API_KEY
    import httpx
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"
    payload = {"idToken": req.idToken}
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        
        if not resp.is_success or "users" not in data or len(data["users"]) == 0:
            raise UnauthorizedError("Invalid Google token")
            
        google_user = data["users"][0]
        email = google_user.get("email")
        display_name = google_user.get("displayName", "User")
        
        if not email:
            raise DomainError("Google account has no email")
            
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            base_username = display_name.replace(" ", "").lower()
            if not base_username:
                base_username = email.split("@")[0]
            
            username = base_username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = User(
                username=username,
                email=email,
                hashed_password="firebase_google_managed",
                preferred_language="en-IN",
                roles="user"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        token_payload = {"user_id": user.id, "username": user.username, "roles": parse_roles(user.roles)}
        token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)
        set_refresh_cookie(response, refresh_token)
        
        return TokenResponse(
            access_token=token,
            username=user.username,
            roles=parse_roles(user.roles),
        )

@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(request: __import__('fastapi').Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise UnauthorizedError("Refresh token missing")
        
    payload = decode_token(refresh_token, expected_type="refresh")
    if not payload:
        raise UnauthorizedError("Invalid or expired refresh token")
        
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise UnauthorizedError("User not found")
        
    new_token = create_access_token({
        "user_id": user.id,
        "username": user.username,
        "roles": parse_roles(user.roles),
    })
    return TokenResponse(
        access_token=new_token,
        username=user.username,
        roles=parse_roles(user.roles),
    )

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "preferred_language": current_user.preferred_language,
        "roles": parse_roles(getattr(current_user, "roles", "user")),
    }

@router.get("/admin/check")
def admin_check(current_user: User = Depends(RoleChecker(["admin"]))):
    return {"status": "ok", "message": "Admin access granted", "user": current_user.username}

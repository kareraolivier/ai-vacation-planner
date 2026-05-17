from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.services.auth import AuthService
from ..core.database import get_db
from ..services.auth import AuthService
from ..schemas.user import UserCreate, UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        auth = AuthService(db)
        result = auth.register_user(user_data)
        return Token(access_token=result["access_token"], token_type=result["token_type"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    auth = AuthService(db)
    result = auth.login_user(user_data.email, user_data.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return Token(access_token=result["access_token"], token_type=result["token_type"])
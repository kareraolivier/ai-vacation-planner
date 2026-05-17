from typing import Optional
from sqlalchemy.orm import Session
from ..repositories.user_repository import UserRepository
from ..core.security import verify_password, get_password_hash, create_access_token
from ..schemas.user import UserCreate, Token
from datetime import timedelta
from ..core.config import settings

class AuthService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
    
    def register_user(self, user_data: UserCreate) -> dict:
        # Check if user exists
        if self.user_repo.get_by_email(user_data.email):
            raise ValueError("Email already registered")
        
        if self.user_repo.get_by_username(user_data.username):
            raise ValueError("Username already taken")
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = self.user_repo.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name
        )
        
        # Create token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    
    def login_user(self, email: str, password: str) -> Optional[dict]:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    
    def get_current_user(self, user_id: int):
        return self.user_repo.get(user_id)
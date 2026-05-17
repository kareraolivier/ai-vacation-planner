from typing import Optional
from sqlalchemy.orm import Session
from .base import BaseRepository
from ..models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.get_by(email=email)
    
    def get_by_username(self, username: str) -> Optional[User]:
        return self.get_by(username=username)
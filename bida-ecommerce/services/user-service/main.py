import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from db import engine, Base, get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse, TokenResponse, UserProfileUpdate
from security import hash_password, verify_password, create_access_token, get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(Khởi tạo bảng PostgreSQL thành công trong User Service)
    except Exception as e:
        logger.error(fLỗi khởi tạo DB PostgreSQL: {e})
    yield

app = FastAPI(title=User & Auth Service, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*],
    allow_credentials=True,
    allow_methods=[*],
    allow_headers=[*],
)

@app.post(/api/auth/register, response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail=Username đã tồn tại)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={sub: new_user.username, user_id: new_user.id, role: new_user.role})
    return {access_token: access_token, token_type: bearer}

@app.post(/api/auth/login, response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail=Sai username hoặc password)
    
    access_token = create_access_token(data={sub: user.username, user_id: user.id, role: user.role})
    return {access_token: access_token, token_type: bearer}

@app.get(/api/auth/me, response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.put(/api/auth/profile, response_model=UserResponse)
def update_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
    if profile_data.address is not None:
        current_user.address = profile_data.address
    if profile_data.email is not None:
        if profile_data.email != current_user.email:
            existing = db.query(User).filter(User.email == profile_data.email).first()
            if existing:
                raise HTTPException(status_code=400, detail=Email đã được sử dụng)
            current_user.email = profile_data.email
            
    db.commit()
    db.refresh(current_user)
    return current_user

@app.get(/healthz)
def health_check():
    return {status: ok, service: user-service}

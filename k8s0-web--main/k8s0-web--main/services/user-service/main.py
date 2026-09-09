import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from db_api_client import user_db_client
from schemas import UserRegister, UserLogin, UserResponse, TokenResponse, UserProfileUpdate
from security import hash_password, verify_password, create_access_token, get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UserService")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("User Service: Khởi động service (Giao tiếp qua Database API)")
    try:
        admin = await user_db_client.find_user(username="admin")
        if not admin:
            await user_db_client.create_user({
                "username": "admin",
                "email": "admin@bidacaocap.com",
                "password_hash": hash_password("admin123"),
                "full_name": "Quản Trị Viên",
                "role": "admin"
            })
            logger.info("Đã tự động tạo tài khoản admin/admin123 qua Database API")
    except Exception as e:
        logger.warning(f"Chưa thể kết nối tới Database API lúc khởi động: {e}")
    yield

app = FastAPI(title='User & Auth Service', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.post('/api/auth/register', response_model=TokenResponse)
async def register(user_data: UserRegister):
    existing_user = await user_db_client.find_user(username=user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail='Username đã tồn tại')
    if user_data.email:
        existing_email = await user_db_client.find_user(email=user_data.email)
        if existing_email:
            raise HTTPException(status_code=400, detail='Email đã được sử dụng')
    
    new_user = await user_db_client.create_user({
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "full_name": user_data.full_name or user_data.username,
        "role": "user"
    })
    
    access_token = create_access_token(data={
        'sub': new_user['username'],
        'user_id': new_user['id'],
        'role': new_user['role']
    })
    return {'access_token': access_token, 'token_type': 'bearer', 'user': new_user}

@app.post('/api/auth/login', response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await user_db_client.find_user(username=user_data.username)
    if not user:
        user = await user_db_client.find_user(email=user_data.username)
        
    if not user or not verify_password(user_data.password, user.get('password_hash', '')):
        raise HTTPException(status_code=400, detail='Sai username hoặc password')
    
    access_token = create_access_token(data={
        'sub': user['username'],
        'user_id': user['id'],
        'role': user['role']
    })
    return {'access_token': access_token, 'token_type': 'bearer', 'user': user}

@app.get('/api/auth/me', response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.put('/api/auth/profile', response_model=UserResponse)
async def update_profile(profile_data: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    update_fields = {}
    if profile_data.full_name is not None:
        update_fields['full_name'] = profile_data.full_name
    if profile_data.phone is not None:
        update_fields['phone'] = profile_data.phone
    if profile_data.address is not None:
        update_fields['address'] = profile_data.address
    if profile_data.email is not None:
        if profile_data.email != current_user.get('email'):
            existing = await user_db_client.find_user(email=profile_data.email)
            if existing:
                raise HTTPException(status_code=400, detail='Email đã được sử dụng')
            update_fields['email'] = profile_data.email

    updated_user = await user_db_client.update_user(current_user['id'], update_fields)
    return updated_user

@app.get('/healthz')
def health_check():
    return {'status': 'ok', 'service': 'user-service'}

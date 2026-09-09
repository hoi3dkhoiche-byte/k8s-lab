import os
from jose import JWTError, jwt
from fastapi import HTTPException, status, Header
from typing import Optional

SECRET_KEY = os.environ.get('SECRET_KEY', 'bida-cao-cap-secret-key-2024')
ALGORITHM = 'HS256'

def get_current_user_claims(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Yêu cầu đăng nhập',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    token = authorization.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token không hợp lệ',
            headers={'WWW-Authenticate': 'Bearer'},
        )

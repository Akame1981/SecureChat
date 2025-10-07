from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ..schemas.auth import Token, LoginRequest
from ..core.config import get_settings
from ..core.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post('/login', response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    settings = get_settings()
    if form_data.username != settings.admin_username or not verify_password(form_data.password, settings.admin_password, settings.admin_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = create_access_token(subject=form_data.username)
    return Token(access_token=token)

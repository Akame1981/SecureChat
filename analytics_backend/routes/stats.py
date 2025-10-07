from fastapi import APIRouter, Depends, HTTPException, status, Header
from ..services.metrics_service import get_system_stats, get_user_stats, get_message_stats
from ..core.security import decode_token

router = APIRouter(prefix="/api/stats", tags=["stats"])

def _auth(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split()[1]
    sub = decode_token(token)
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return sub

@router.get('/system')
async def system_stats(user=Depends(_auth)):
    return get_system_stats()

@router.get('/users')
async def user_stats(user=Depends(_auth)):
    return get_user_stats()

@router.get('/messages')
async def message_stats(user=Depends(_auth)):
    return get_message_stats()

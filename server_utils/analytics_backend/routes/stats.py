from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from ..services.metrics_service import get_system_stats, get_user_stats, get_message_stats, get_attachment_stats
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

@router.get('/attachments')
async def attachment_stats(user=Depends(_auth)):
    return get_attachment_stats()

@router.get('/export.csv')
async def export_csv(user=Depends(_auth)):
    sys_stats = get_system_stats()
    user_stats = get_user_stats()
    msg_stats = get_message_stats()
    att_stats = get_attachment_stats()
    # Simple flat CSV (could be expanded)
    lines = [
        'category,key,value',
        *[f'system,{k},{v}' for k,v in sys_stats.items()],
        *[f'users,{k},{v}' for k,v in user_stats.items()],
        f'messages,messages_today,{msg_stats["messages_today"]}',
        f'messages,avg_message_size,{msg_stats["avg_message_size"]}',
        f'messages,bytes_today,{msg_stats.get("bytes_today",0)}',
        f'messages,total_bytes,{msg_stats.get("total_bytes",0)}',
        f'messages,total_mb,{msg_stats.get("total_mb",0)}',
        f'messages,total_gb,{msg_stats.get("total_gb",0)}',
        f'attachments,attachments_today,{att_stats["attachments_today"]}',
        f'attachments,avg_attachment_size,{att_stats["avg_attachment_size"]}',
        f'attachments,bytes_today,{att_stats.get("bytes_today",0)}',
        f'attachments,total_bytes,{att_stats.get("total_bytes",0)}',
        f'attachments,total_mb,{att_stats.get("total_mb",0)}',
        f'attachments,total_gb,{att_stats.get("total_gb",0)}'
    ]
    content = '\n'.join(lines)
    return Response(content, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="analytics_export.csv"'})

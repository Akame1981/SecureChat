from fastapi import APIRouter, HTTPException, Header, status, Body, File, UploadFile, Request
import base64
from typing import Optional
import json
import os
import hashlib
from fastapi.responses import StreamingResponse
import secrets
import time
import re

from .db import SessionLocal, init_db, Group, GroupMember, Channel, GroupMessage, ChannelMeta
from .schemas import (
    CreateGroupRequest,
    CreateGroupResponse,
    JoinGroupRequest,
    LeaveGroupRequest,
    ListGroupsResponse,
    GroupInfo,
    CreateChannelRequest,
    RenameChannelRequest,
    SendGroupMessageRequest,
    FetchGroupMessagesRequest,
)


router = APIRouter(prefix="/groups", tags=["groups"])

# Ensure DB schema is ready on module import
init_db()


def _require_member(db, group_id: str, user_id: str) -> GroupMember:
    gm = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id, GroupMember.pending == False).first()
    if not gm:
        raise HTTPException(status_code=403, detail="Not a group member")
    return gm


@router.post("/create", response_model=CreateGroupResponse)
def create_group(req: CreateGroupRequest):
    db = SessionLocal()
    try:
        invite_code = secrets.token_urlsafe(8)
        g = Group(name=req.name, owner_id=req.owner_id, is_public=req.is_public, invite_code=invite_code, key_version=1)
        db.add(g)
        db.flush()
        # Default text channel "general"
        ch = Channel(group_id=g.id, name="general", type="text")
        db.add(ch)
        # Owner as member (owner role); encrypted_group_key set by clients later
        gm = GroupMember(group_id=g.id, user_id=req.owner_id, role="owner", encrypted_group_key=None, key_version=1, pending=False)
        db.add(gm)
        db.commit()
        return CreateGroupResponse(id=g.id, invite_code=invite_code)
    finally:
        db.close()


@router.post("/join")
def join_group(req: JoinGroupRequest):
    db = SessionLocal()
    try:
        g: Optional[Group] = None
        if req.invite_code:
            g = db.query(Group).filter(Group.invite_code == req.invite_code).first()
            if not g:
                raise HTTPException(status_code=404, detail="Invalid invite code")
        elif req.group_id:
            g = db.query(Group).filter(Group.id == req.group_id).first()
            if not g:
                raise HTTPException(status_code=404, detail="Group not found")
        else:
            raise HTTPException(status_code=400, detail="invite_code or group_id required")

        existing = db.query(GroupMember).filter(GroupMember.group_id == g.id, GroupMember.user_id == req.user_id).first()
        if existing and not existing.pending:
            return {"status": "already_member", "group_id": g.id}

        if g.is_public or req.invite_code:
            if existing:
                existing.pending = False
            else:
                db.add(GroupMember(group_id=g.id, user_id=req.user_id, role="member", encrypted_group_key=None, key_version=g.key_version, pending=False))
            db.commit()
            return {"status": "joined", "group_id": g.id, "key_version": g.key_version}
        else:
            # Admin approval flow -> create pending request
            if existing:
                existing.pending = True
            else:
                db.add(GroupMember(group_id=g.id, user_id=req.user_id, role="member", encrypted_group_key=None, key_version=g.key_version, pending=True))
            db.commit()
            return {"status": "pending", "group_id": g.id}
    finally:
        db.close()


@router.post("/approve")
def approve_member(req: JoinGroupRequest):
    if not req.group_id or not req.approve_user_id or not req.user_id:
        raise HTTPException(status_code=400, detail="group_id, approve_user_id, user_id required")
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == req.group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        approver = db.query(GroupMember).filter(GroupMember.group_id == g.id, GroupMember.user_id == req.user_id).first()
        if not approver or approver.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Only admins/owner can approve")
        pending = db.query(GroupMember).filter(GroupMember.group_id == g.id, GroupMember.user_id == req.approve_user_id).first()
        if not pending:
            raise HTTPException(status_code=404, detail="Pending request not found")
        pending.pending = False
        db.commit()
        return {"status": "approved"}
    finally:
        db.close()


@router.post("/leave")
def leave_group(req: LeaveGroupRequest):
    db = SessionLocal()
    try:
        mem = db.query(GroupMember).filter(GroupMember.group_id == req.group_id, GroupMember.user_id == req.user_id).first()
        if not mem:
            return {"status": "not_member"}
        db.delete(mem)
        # Increment key_version on group to indicate clients must rotate
        g = db.query(Group).filter(Group.id == req.group_id).first()
        if g:
            g.key_version = int((g.key_version or 1) + 1)
        db.commit()
        return {"status": "left", "new_key_version": g.key_version if g else None}
    finally:
        db.close()


@router.get("/list", response_model=ListGroupsResponse)
def list_groups(user_id: str):
    db = SessionLocal()
    try:
        # Only non-pending memberships
        q = (
            db.query(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .filter(GroupMember.user_id == user_id, GroupMember.pending == False)
        )
        groups = [
            GroupInfo(
                id=g.id,
                name=g.name,
                is_public=bool(g.is_public),
                owner_id=g.owner_id,
                key_version=int(g.key_version or 1),
            )
            for g in q.all()
        ]
        return ListGroupsResponse(groups=groups)
    finally:
        db.close()


@router.get("/discover")
def discover_public_groups(query: Optional[str] = None, limit: int = 50):
    db = SessionLocal()
    try:
        q = db.query(Group).filter(Group.is_public == True)
        if query:
            # SQLite lacks ILIKE; emulate case-insensitive search
            pattern = f"%{query.lower()}%"
            from sqlalchemy import func
            q = q.filter(func.lower(Group.name).like(pattern))
        q = q.order_by(Group.created_at.desc()).limit(int(limit))
        items = [
            {
                "id": g.id,
                "name": g.name,
                "owner_id": g.owner_id,
                "invite_code": g.invite_code,
                "key_version": int(g.key_version or 1),
                "created_at": g.created_at,
            }
            for g in q.all()
        ]
        return {"groups": items}
    finally:
        db.close()


@router.post("/channels/create")
def create_channel(req: CreateChannelRequest, user_id: str):
    db = SessionLocal()
    try:
        gm = _require_member(db, req.group_id, user_id)
        # Only the group owner may create channels
        if gm.role != "owner":
            raise HTTPException(status_code=403, detail="Only the group owner can create channels")
        ch = Channel(group_id=req.group_id, name=req.name, type=req.type or "text")
        db.add(ch)
        db.commit()
        return {"status": "created", "channel_id": ch.id}
    finally:
        db.close()


@router.post("/rename")
def rename_group(group_id: str = Body(...), new_name: str = Body(...), user_id: str = Body(...)):
    """Rename a group. Only owner/admin may rename."""
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not actor or actor.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        g.name = new_name
        db.commit()
        return {"status": "renamed", "name": g.name}
    finally:
        db.close()
    


@router.post("/channels/rename")
def rename_channel(req: RenameChannelRequest, user_id: str):
    db = SessionLocal()
    try:
        ch = db.query(Channel).filter(Channel.id == req.channel_id).first()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        gm = _require_member(db, ch.group_id, user_id)
        # Only admins/owner can rename for now
        if gm.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        ch.name = req.name
        db.commit()
        return {"status": "renamed"}
    finally:
        db.close()


@router.post("/channels/delete")
def delete_channel(channel_id: str, user_id: str):
    db = SessionLocal()
    try:
        ch = db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        gm = _require_member(db, ch.group_id, user_id)
        # Only admins/owner can delete a channel
        if gm.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        # Deleting channel will cascade delete its messages due to FK ondelete
        db.delete(ch)
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()


@router.get("/channels/list")
def list_channels(group_id: str, user_id: str):
    db = SessionLocal()
    try:
        _require_member(db, group_id, user_id)
        rows = db.query(Channel).filter(Channel.group_id == group_id).order_by(Channel.created_at.asc()).all()
        return {
            "channels": [
                {"id": c.id, "group_id": c.group_id, "name": c.name, "type": c.type, "created_at": c.created_at}
                for c in rows
            ]
        }
    finally:
        db.close()


@router.get("/channels/meta")
def get_channel_meta(channel_id: str, user_id: str):
    db = SessionLocal()
    try:
        ch = db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        _require_member(db, ch.group_id, user_id)
        meta = db.query(ChannelMeta).filter(ChannelMeta.channel_id == channel_id).first()
        return {
            "topic": meta.topic if meta else None,
            "description": meta.description if meta else None,
        }
    finally:
        db.close()


@router.post("/channels/meta/set")
def set_channel_meta(channel_id: str, user_id: str, topic: str | None = None, description: str | None = None):
    db = SessionLocal()
    try:
        ch = db.query(Channel).filter(Channel.id == channel_id).first()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        gm = _require_member(db, ch.group_id, user_id)
        # Allow any member to edit topic/description for now; adjust if needed
        meta = db.query(ChannelMeta).filter(ChannelMeta.channel_id == channel_id).first()
        if not meta:
            meta = ChannelMeta(channel_id=channel_id)
            db.add(meta)
        meta.topic = topic
        meta.description = description
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@router.get("/channels/role")
def get_my_role(group_id: str, user_id: str):
    db = SessionLocal()
    try:
        gm = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id, GroupMember.pending == False).first()
        if not gm:
            raise HTTPException(status_code=403, detail="Not a member")
        return {"role": gm.role}
    finally:
        db.close()


@router.post("/messages/send")
def send_group_message(req: SendGroupMessageRequest):
    db = SessionLocal()
    try:
        # Validate membership and version
        gm = _require_member(db, req.group_id, req.sender_id)
        g = db.query(Group).filter(Group.id == req.group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        if int(req.key_version) != int(g.key_version or 1):
            raise HTTPException(status_code=409, detail="Key version mismatch")
        # Save ciphertext only
        msg = GroupMessage(
            group_id=req.group_id,
            channel_id=req.channel_id,
            sender_id=req.sender_id,
            ciphertext=req.ciphertext,
            nonce=req.nonce,
            attachment_meta=(json.dumps(req.attachment_meta) if req.attachment_meta else None),
            key_version=req.key_version,
            timestamp=req.timestamp or time.time(),
        )
        db.add(msg)
        db.commit()
        return {"status": "ok", "id": msg.id, "timestamp": msg.timestamp}
    finally:
        db.close()


@router.post("/messages/fetch")
def fetch_group_messages(req: FetchGroupMessagesRequest, user_id: str):
    db = SessionLocal()
    try:
        _require_member(db, req.group_id, user_id)
        q = (
            db.query(GroupMessage)
            .filter(
                GroupMessage.group_id == req.group_id,
                GroupMessage.channel_id == req.channel_id,
                GroupMessage.timestamp > (req.since or 0.0),
            )
            .order_by(GroupMessage.timestamp.asc())
        )
        if req.limit:
            q = q.limit(int(req.limit))
        rows = q.all()
        return {
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.sender_id,
                    "ciphertext": m.ciphertext,
                    "nonce": m.nonce,
                    "_attachment_json": m.attachment_meta,
                    "key_version": m.key_version,
                    "timestamp": m.timestamp,
                }
                for m in rows
            ]
        }
    finally:
        db.close()


@router.get("/members/keys")
def get_member_keys(group_id: str):
    """Return members and their encrypted_group_key for client distribution or reconciliation.

    Clients should update encrypted_group_key when rekeying.
    """
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        ms = (
            db.query(GroupMember)
            .filter(GroupMember.group_id == group_id, GroupMember.pending == False)
            .all()
        )
        return {
            "key_version": g.key_version,
            "members": [
                {
                    "user_id": m.user_id,
                    "role": m.role,
                    "encrypted_group_key": m.encrypted_group_key,
                    "key_version": m.key_version,
                }
                for m in ms
            ],
        }
    finally:
        db.close()


@router.post("/members/keys/update")
def update_member_key(group_id: str, user_id: str, encrypted_key_b64: str, key_version: int):
    db = SessionLocal()
    try:
        m = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")
        m.encrypted_group_key = encrypted_key_b64
        m.key_version = key_version
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@router.post("/invites/rotate")
def rotate_invite(group_id: str, user_id: str):
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        gm = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not gm or gm.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        import secrets
        g.invite_code = secrets.token_urlsafe(8)
        db.commit()
        return {"invite_code": g.invite_code}
    finally:
        db.close()


@router.post("/members/ban")
def ban_member(group_id: str, target_user_id: str, user_id: str):
    """Admin/owner removes a member from the group and bumps key_version.

    Clients must rekey. Server only updates version; key distribution is client-driven.
    """
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not actor or actor.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        target = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == target_user_id).first()
        if not target:
            return {"status": "not_member"}
        db.delete(target)
        g.key_version = int((g.key_version or 1) + 1)
        db.commit()
        return {"status": "banned", "new_key_version": g.key_version}
    finally:
        db.close()


@router.post("/rekey")
def rekey_group(group_id: str, user_id: str):
    """Owner/Admin requests key_version increment. Clients then distribute new key."""
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not actor or actor.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        g.key_version = int((g.key_version or 1) + 1)
        db.commit()
        return {"key_version": g.key_version}
    finally:
        db.close()


@router.post('/members/transfer_owner')
def transfer_owner(group_id: str, new_owner_user_id: str, user_id: str):
    """Transfer ownership of the group to another existing member. Only current owner may transfer."""
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not actor or actor.role != 'owner':
            raise HTTPException(status_code=403, detail="Only the owner may transfer ownership")
        target = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == new_owner_user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target user not a member")
        # Demote current owner to admin
        actor.role = 'admin'
        # Promote target to owner
        target.role = 'owner'
        # Update group's owner_id
        g.owner_id = new_owner_user_id
        db.commit()
        return {"status": "transferred", "new_owner": new_owner_user_id}
    finally:
        db.close()


@router.post("/public/set")
def set_group_public(group_id: str, is_public: bool, user_id: str):
    """Owner/Admin can toggle whether a group is publicly discoverable/joinable without approval."""
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
        if not actor or actor.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        g.is_public = bool(is_public)
        db.commit()
        return {"is_public": bool(g.is_public)}
    finally:
        db.close()


# ----- Admin / management endpoints -----
@router.get("/public/list")
def list_all_public_groups(query: Optional[str] = None, limit: int = 200):
    """Return all public groups (for admin/management UI). Supports optional case-insensitive name filter."""
    db = SessionLocal()
    try:
        q = db.query(Group).filter(Group.is_public == True)
        if query:
            pattern = f"%{query.lower()}%"
            from sqlalchemy import func
            q = q.filter(func.lower(Group.name).like(pattern))
        q = q.order_by(Group.created_at.desc()).limit(int(limit))
        items = [
            {
                "id": g.id,
                "name": g.name,
                "owner_id": g.owner_id,
                "invite_code": g.invite_code,
                "key_version": int(g.key_version or 1),
                "created_at": g.created_at,
            }
            for g in q.all()
        ]
        return {"groups": items}
    finally:
        db.close()


@router.delete("/delete")
def delete_group(group_id: str, user_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Delete a group and its associated data.

    If `user_id` is supplied, require that the actor be owner/admin; if omitted
    this call is treated as an administrative action (for example from the
    analytics/admin UI) and will delete the group without member permission checks.
    """
    db = SessionLocal()
    try:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g:
            raise HTTPException(status_code=404, detail="Group not found")
        # If an Authorization header with a bearer token is present and decodes
        # to the configured admin username, allow deletion as an admin action.
        # Otherwise, if a user_id is provided enforce owner/admin membership.
        from server_utils.analytics_backend.core.security import decode_token
        from server_utils.analytics_backend.core.config import get_settings

        settings = get_settings()
        is_admin_token = False
        if authorization and authorization.lower().startswith('bearer '):
            token = authorization.split()[1]
            sub = decode_token(token)
            if sub and sub == settings.admin_username:
                is_admin_token = True

        if not is_admin_token:
            # Require explicit user_id and membership check for non-admins
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
            actor = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
            if not actor or actor.role not in ("owner", "admin"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        # Deleting the group will cascade to channels, messages, members due to FK ondelete
        db.delete(g)
        db.commit()
        return {"status": "deleted"}
    finally:
        db.close()


# Attachment storage directory (raw encrypted blobs sent by clients)
ATT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/attachments'))
os.makedirs(ATT_DIR, exist_ok=True)


@router.post('/attachments/upload')
async def upload_attachment(group_id: str, user_id: str, request: Request, file: bytes = Body(None), upload_file: UploadFile = File(None)):
    """Accept an already-encrypted attachment blob from a group member and store it.

    The client is expected to encrypt attachments end-to-end. The server stores the raw
    bytes under a deterministic sha256 filename and returns the attachment id.
    """
    db = SessionLocal()
    try:
        # membership check
        _require_member(db, group_id, user_id)
        data = None
        # 1) direct Body param (synchronous clients may bind to 'file')
        if file is not None:
            data = file
        # 2) multipart UploadFile
        elif upload_file is not None:
            try:
                data = await upload_file.read()
            except Exception:
                data = None
        # 3) JSON payload with base64 blob (compat with recipient uploader which used JSON)
        if data is None:
            ctype = request.headers.get('content-type', '')
            if 'application/json' in ctype:
                try:
                    body = await request.json()
                    # support keys: blob, file_b64, file, blob_b64
                    for k in ('blob', 'file_b64', 'file', 'blob_b64'):
                        if isinstance(body, dict) and body.get(k):
                            try:
                                data = base64.b64decode(body.get(k))
                                break
                            except Exception:
                                data = None
                except Exception:
                    data = None
        # 4) raw body fallback (some clients POST raw bytes without binding to param)
        if data is None:
            try:
                raw = await request.body()
                if raw:
                    data = raw
            except Exception:
                data = None

        if not data:
            raise HTTPException(status_code=400, detail="No file provided")

        h = hashlib.sha256(data).hexdigest()
        path = os.path.join(ATT_DIR, f"{h}.bin")
        if not os.path.exists(path):
            tmp = path + '.tmp'
            with open(tmp, 'wb') as f:
                f.write(data)
                try: f.flush(); os.fsync(f.fileno())
                except Exception: pass
            os.replace(tmp, path)
        return {"id": h, "size": len(data)}
    finally:
        db.close()


@router.get('/attachments/{att_id}')
def download_attachment(att_id: str, group_id: str = None, user_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Stream back the raw attachment blob if the requester is a group member or an admin token.

    If group_id and user_id are omitted, an admin bearer token (analytics) is required.
    """
    db = SessionLocal()
    try:
        is_admin_token = False
        if authorization and authorization.lower().startswith('bearer '):
            from server_utils.analytics_backend.core.security import decode_token
            from server_utils.analytics_backend.core.config import get_settings
            settings = get_settings()
            token = authorization.split()[1]
            sub = decode_token(token)
            if sub and sub == settings.admin_username:
                is_admin_token = True

        if not is_admin_token:
            if not group_id or not user_id:
                raise HTTPException(status_code=401, detail='Authentication required')
            _require_member(db, group_id, user_id)

        # Validate att_id strictly: must be the sha256 hex (64 lowercase hex chars).
        # Reject any other format to avoid path injection or unexpected file access.
        if not isinstance(att_id, str) or not re.fullmatch(r"[0-9a-f]{64}", att_id):
            raise HTTPException(status_code=404, detail='Attachment not found')

        path = os.path.join(ATT_DIR, f"{att_id}.bin")
        real = os.path.realpath(path)
        if not real.startswith(os.path.realpath(ATT_DIR)):
            raise HTTPException(status_code=404, detail="Attachment not found")

        def iterfile():
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        return StreamingResponse(iterfile(), media_type='application/octet-stream')
    finally:
        db.close()

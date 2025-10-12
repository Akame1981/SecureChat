from typing import Optional, List
from pydantic import BaseModel


class CreateGroupRequest(BaseModel):
    name: str
    is_public: bool = False
    owner_id: str  # creator's encryption public key hex


class CreateGroupResponse(BaseModel):
    id: str
    invite_code: str


class JoinGroupRequest(BaseModel):
    user_id: str
    invite_code: Optional[str] = None
    group_id: Optional[str] = None
    approve_user_id: Optional[str] = None  # for admin approval


class LeaveGroupRequest(BaseModel):
    user_id: str
    group_id: str


class GroupInfo(BaseModel):
    id: str
    name: str
    is_public: bool
    server_distribute: bool = False
    server_store_history: bool = False
    owner_id: str
    key_version: int


class ListGroupsResponse(BaseModel):
    groups: List[GroupInfo]


class CreateChannelRequest(BaseModel):
    group_id: str
    name: str
    type: str = "text"


class RenameChannelRequest(BaseModel):
    channel_id: str
    name: str


class SendGroupMessageRequest(BaseModel):
    group_id: str
    channel_id: str
    sender_id: str
    ciphertext: str
    nonce: str
    key_version: int
    timestamp: Optional[float] = None
    attachment_meta: Optional[dict] = None


class FetchGroupMessagesRequest(BaseModel):
    group_id: str
    channel_id: str
    since: Optional[float] = None
    limit: Optional[int] = 200

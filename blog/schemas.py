from pydantic import BaseModel
from typing import List

# Comment schemas
class CommentCreate(BaseModel):
    content: str
    post_id: int
    user_id: int = None

    class config:
        from_attribute = True


class CommentOut(BaseModel):
    id: int
    content: str
    user_id: int  # Can be None if no user association
    post_id: int

    class Config:
        from_mode = True


class LikeOut(BaseModel):
    id: int
    user_id: int
    post_id: int

    class Config:
        from_mode = True

# Post schemas
class PostCreate(BaseModel):
    title: str
    content: str

class PostOut(BaseModel):
    id: int
    title: str
    content: str
    comments: List[CommentOut] = []
    likes: List[LikeOut] = []
    like_count: int  # Display like count

    class Config:
        from_mode = True

# User schemas
class UserCreate(BaseModel):
    username: str
    password: str
    role: str

    class Config:
        from_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

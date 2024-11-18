from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from datetime import timedelta
from database import engine, Base, SessionLocal, User, Post, Comment, Like
from schemas import PostCreate, PostOut, CommentCreate, CommentOut, LikeOut, UserCreate, Token
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

# FastAPI app
app = FastAPI()

# Database initialization (recreate tables at startup)
@app.on_event("startup")
def startup():
    # Drop all tables (WARNING: This will delete all data)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Register new user
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User registered successfully"}

# Login and generate token
@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Create new post
@app.post("/posts/", response_model=PostOut)
def create_post(post: PostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_post = Post(title=post.title, content=post.content, user_id=current_user.id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

# Get all posts with like count and comments (no authentication required)
@app.get("/posts/", response_model=list[PostOut])
def read_posts(db: Session = Depends(get_db)):
    # Use joinedload to eagerly load the associated likes and comments
    posts = db.query(Post).options(joinedload(Post.likes), joinedload(Post.comments)).all()
    return posts

@app.post("/comments/{post_id}", response_model=CommentOut)
def create_comment(post_id: int, comment: CommentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Use the authenticated user's `user_id`
    new_comment = Comment(content=comment.content, post_id=post_id, user_id=current_user.id)
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


# Like a post (no authentication required)
@app.post("/likes/{post_id}", response_model=LikeOut)
def like_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if the post has already been liked (no user validation for now)
    db_like = db.query(Like).filter(Like.post_id == post_id).first()
    if db_like:
        raise HTTPException(status_code=400, detail="You have already liked this post")
    
    # Add the like
    new_like = Like(post_id=post_id, user_id=None)  # No user validation
    db.add(new_like)
    db.commit()
    db.refresh(new_like)

    # After adding the like, get the updated post and like details
    db_post = db.query(Post).filter(Post.id == post_id).first()  # Refresh the post data
    
    # Construct response in the form of LikeOut
    return LikeOut(
        id=new_like.id,           # ID of the like
        user_id=None,             # Set user_id to None (no user validation)
        post_id=post_id,          # ID of the post that was liked
    )

# Unlike a post
@app.delete("/likes/{post_id}")
def unlike_post(post_id: int, db: Session = Depends(get_db)):
    db_like = db.query(Like).filter(Like.post_id == post_id).first()
    if not db_like:
        raise HTTPException(status_code=404, detail="Like not found")
    
    db.delete(db_like)
    db.commit()
    return {"msg": "Like removed"}

# Get all likes for a post
@app.get("/likes/{post_id}", response_model=list[LikeOut])
def get_likes(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Return all likes for the post
    return db_post.likes

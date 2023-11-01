import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from os import getenv
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

SECRET_KEY = getenv('SECRET_KEY_VAR')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Database connection setup
async def connect_to_db():
    conn = await asyncpg.connect(
        user=getenv('USERNAME'),
        password=getenv('PASSWORD'),
        database=getenv('DBNAME'),
        host=getenv('ENDPOINT'),
        port=5432
    )
    print("Connection Setup Successful")
    return conn

# Create the table on startup
@app.on_event("startup")
async def startup_db():
    conn = await connect_to_db()
    await create_table(conn)

# Function to create the table if it doesn't exist
async def create_table(conn):
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS login_cred (
            username VARCHAR(50) PRIMARY KEY,
            password TEXT
        )
        """
    )


# Token generation and verification
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), conn = Depends(connect_to_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = await conn.fetchrow("SELECT * FROM login_cred WHERE username = $1", username)
        if user is None:
            raise credentials_exception
        
        # Retrieve the expiration time from the token's payload
        expiration_time = payload.get("exp")
        if expiration_time is None or datetime.utcfromtimestamp(expiration_time) < datetime.utcnow():
            raise credentials_exception  # Token has expired
        
        return User(username=user['username'], password=user['password'])
    except jwt.JWTError:
        raise credentials_exception
    
# Register endpoint
@app.post("/register", response_model=Token)
async def register_user(form_data: OAuth2PasswordRequestForm = Depends(), conn = Depends(connect_to_db)):
    username = form_data.username
    password = form_data.password
    hashed_password = pwd_context.hash(password)
    query = "INSERT INTO login_cred (username, password) VALUES ($1, $2) ON CONFLICT DO NOTHING"
    await conn.execute(query, username, hashed_password)
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "Registered Successfully"}


# Login endpoint
@app.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), conn = Depends(connect_to_db)):
    username = form_data.username
    password = form_data.password
    user = await conn.fetchrow("SELECT * FROM login_cred WHERE username = $1", username)
    if user is None or not pwd_context.verify(password, user['password']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}

# New secured API endpoint
@app.get("/embeddings")
async def embeddings(current_user: User = Depends(get_current_user)):
    return {"message": "This is a secured endpoint", "user": current_user.username}
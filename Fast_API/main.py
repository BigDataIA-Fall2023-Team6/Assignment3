from pydantic import BaseModel
from typing import List
import pandas as pd
from scipy.spatial import distance
import ast
import openai
from transformers import GPT2TokenizerFast
# from decouple import config
import os
import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

SECRET_KEY = os.getenv('SECRET_KEY_VAR')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define the GPT-3 model and other parameters
GPT_MODEL = "gpt-3.5-turbo"
api_key = os.environ.get('API_KEY')  # Replace with your actual OpenAI API key
openai.api_key = api_key

# Load the CSV file with embeddings
embeddings_file_path = 'pdf_data.csv'  # Update with the path to your CSV file
df = pd.read_csv(embeddings_file_path)

# Convert the embeddings from string to list
df['Embedding'] = df['Embedding'].apply(ast.literal_eval)


def num_tokens(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    encoding = tokenizer.encode(text, add_special_tokens=False)
    return len(encoding)

# Function to calculate cosine similarity
def cosine_similarity(embedding1, embedding2):
    return 1 - distance.cosine(embedding1, embedding2)

# Define a search function
def strings_ranked_by_relatedness(query, df, relatedness_fn=cosine_similarity, top_n=100):
    query_embedding = generate_text_embeddings(query)  # Implement this function using the OpenAI Text Embedding API
    strings_and_relatednesses = [
        (row['Chunk Text'], relatedness_fn(query_embedding, row['Embedding']))
        for _, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
    strings, relatednesses = zip(*strings_and_relatednesses)
    return strings[:top_n], relatednesses[:top_n]

# Define a function to generate embeddings from text using OpenAI Text Embedding API
def generate_text_embeddings(text, model="text-embedding-ada-002"):
    response = openai.Embedding.create(model=model, input=text)
    return response['data'][0]['embedding']

token_budget = 4096 - 500  # Adjust the token budget as needed
# Function to create a query message from the user's question
def query_message(query, df, token_budget):
    strings, relatednesses = strings_ranked_by_relatedness(query, df)
    introduction = 'Use the below PDFs on the SEC forms to answer the subsequent question. If the answer cannot be found in the articles, write "I could not find an answer."'
    question = f'\n\nQuestion: {query}'
    message = introduction

    # Process each section separately
    for string in strings:
        # Split the content into smaller sections, e.g., paragraphs
        sections = string.split('\n\n')  # You can use a more appropriate separator
        
        for section in sections:
            next_section = f'\n\nSection:\n"""\n{section}\n"""'
            if num_tokens(message + next_section + question) > token_budget:
                break
            else:
                message += next_section

    # return message
    return message + question

# Function to answer questions using GPT
def ask(query, df, GPT_MODEL, token_budget, print_message=False):
    message = query_message(query, df, token_budget=token_budget)
    if print_message:
        # print(message)
        messages = [
            {"role": "system", "content": "You answer questions about the SEC pdfs"},
            {"role": "user", "content": message},
        ]
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0
        )
        response_message = response["choices"][0]["message"]["content"]
        # answer = response_message.split("Section:\n")[0]
    return response_message

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Database connection setup
async def connect_to_db():
    conn = await asyncpg.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        database=os.getenv('DBNAME'),
        host=os.getenv('ENDPOINT'),
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


# FastAPI route to answer questions
class Question(BaseModel):
    query: str

class Answer(BaseModel):
    answer: str

@app.post("/ask", response_model=Answer)
def get_answer(question: Question):
    response = ask(question.query, df, GPT_MODEL, token_budget=4096 - 500,print_message=True)  # Adjust token budget as needed
    return {"answer": response}
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))



SECRET_KEY = "CHANGE_THIS_TO_YOUR_SECRET" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

fake_users_db = {
    "student": {
        "username": "student",
        "password": "123456",  
    }
}


chat_histories: dict[str, list[dict]] = {}

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatRequest(BaseModel):
    message: str
    remember_history: bool = True  

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatMessage]


app = FastAPI(title="WK11 Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",  
        "https://ai-chatroom-test-jccg.vercel.app/ ",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()

def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_username(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    username: str | None = payload.get("sub")
    if username is None or username not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
        )
    return username


def call_llm(messages: list[dict]) -> str:
    try:
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"]
                break

        if not last_user_msg:
            return "我沒有收到訊息，再試一次？"

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=last_user_msg
        )

        return resp.text.strip()

    except Exception as e:
        return f"(LLM 呼叫失敗：{e})"




@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(request: LoginRequest):

    user = fake_users_db.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤"
        )

    token = create_access_token(username=request.username)
    return LoginResponse(access_token=token)


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest, username: str = Depends(get_current_username)):

    user_history = chat_histories.setdefault(username, [])

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant in a simple student chatroom.",
        }
    ]

    if request.remember_history:
        messages.extend(user_history)

    messages.append({"role": "user", "content": request.message})

    reply_text = call_llm(messages)

    if request.remember_history:
        user_history.append({"role": "user", "content": request.message})
        user_history.append({"role": "assistant", "content": reply_text})

    history_for_frontend = [
        ChatMessage(role=m["role"], content=m["content"]) for m in user_history
    ]

    return ChatResponse(
        reply=reply_text,
        history=history_for_frontend if request.remember_history else [],
    )


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "WK11 Chat API running"}

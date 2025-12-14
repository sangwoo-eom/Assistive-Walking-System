# main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path

from core.config import settings
from core.model_manager import load_models
from routes import inference as inference_routes
from routes import stt
from routes import identity 


# ------------------------
# 앱 생성
# ------------------------
app = FastAPI(
    title="Assistive Walking System API",
    version="1.0.0"
)

# ------------------------
# CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# static / templates 경로
# ------------------------
BASE_DIR = Path(__file__).resolve().parent

# 정적 파일
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# 템플릿
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ------------------------
# 서버 시작 시 모델 로딩
# ------------------------
@app.on_event("startup")
async def startup_event():
    load_models()


# ------------------------
# API 라우터
# ------------------------
app.include_router(inference_routes.router, prefix="/api", tags=["inference"])
app.include_router(stt.router, prefix="/api", tags=["stt"])
app.include_router(identity.router, prefix="/api/identity", tags=["identity"]) 


# ------------------------
# 메인 페이지
# ------------------------
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# main.py
# v2
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.db import create_tables
from routers import auth, friends, groups, location

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Serlok API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://serlok-frontend.vercel.app"
],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/auth",     tags=["Auth"])
app.include_router(friends.router,  prefix="/friends",  tags=["Friends"])
app.include_router(groups.router,   prefix="/groups",   tags=["Groups"])
app.include_router(location.router, prefix="/location", tags=["Location"])

@app.get("/")
def root():
    return {"status": "ok", "app": "Serlok"}

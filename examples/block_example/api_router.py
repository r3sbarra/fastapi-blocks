from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/")
async def read_root(request: Request):
    return { "message" : "received" }
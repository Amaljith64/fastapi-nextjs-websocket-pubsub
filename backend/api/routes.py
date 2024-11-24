from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form,Request
from typing import List
from sqlalchemy.orm import Session
import uuid
from fastapi import WebSocket
from schemas import ConversionResponse,JobStatusResponse,JobListResponse
from database import get_db
from config import Settings
from services.image_service import ImageService
from middleware.ratelimit import rate_limit



router = APIRouter()
settings = Settings()

@router.post('/upload/',response_model=ConversionResponse)
@rate_limit()
async def upload_images(
    request: Request,
    files : List[UploadFile] = File(...),
    output_format : str = Form(...),
    session_id: str = Form(...),
    db : Session = Depends(get_db)
):
    image_service = ImageService(settings)
    return await image_service.process_uploads(files,output_format,session_id,db)

import json
from fastapi import HTTPException, UploadFile
from typing import List
from sqlalchemy.orm import Session
import uuid
from pathlib import Path
from config import Settings
from models import ConversionJob, ConversionStatus
from worker import convert_image
from redis import Redis

class ImageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,decode_responses=True)

    def _get_redis_key(self, session_id: str) -> str:
        return f"task_status_{session_id}"

    async def validate_image(self, file: UploadFile) -> bool:
        if file.size > self.settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400,detail="file too large")
        
        ext = file.filename.split('.')[-1].lower()
        if ext not in self.settings.ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail="Unsuported File formar")
        
        return True
    
    async def process_uploads(
            self,
            files: List[UploadFile],
            output_format: str,
            session_id:str,
            db : Session
    ):
        if output_format.lower() not in self.settings.ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail="Format not allowed ")
        
        results = []

        for file in files:
            result = await self._process_single_file(file, output_format,session_id, db)
            results.append(result)

        return {"success": True, "jobs": results}

    
    async def _process_single_file(
            self,
            file:UploadFile,
            output_format:str,
            session_id:str,
            db:Session
    ):
        input_path = None

        try:
            await self.validate_image(file)

            job_id = str(uuid.uuid4())
            input_filename = f"{job_id}{Path(file.filename).suffix}"
            input_path = self.settings.UPLOAD_DIR / input_filename

            file_content = await file.read()

            with open(input_path,'wb') as buffer:
                buffer.write(file_content)

            job = ConversionJob(
                id=job_id,
                input_path=input_filename,
                output_format=output_format,
                status=ConversionStatus.QUEUED

            )
            db.add(job)
            db.commit()

            # Add initial status to Redis
            status_data = {
                "status": ConversionStatus.QUEUED,
                "session_id": session_id,
                "job_id":job_id,
                "input_path": f"/uploads/{input_filename}",
                "output_path": None,
                "output_format": output_format,
                "error": None
            }

            self.redis.publish(self._get_redis_key(session_id),
                           json.dumps(status_data))


            convert_image.delay(job_id,output_format,session_id)

            return {
                'job_id': job_id,
                'session_id':session_id,
                'filename': file.filename,
                'status': 'queued'
            }
        
        except Exception as e:
            db.rollback()
            if input_path and Path(input_path).exists():
                Path(input_path).unlink()

            raise HTTPException(status_code=500, detail=str(e))
        
        finally:
            await file.close()

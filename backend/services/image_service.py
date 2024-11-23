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

    def _get_redis_key(self, job_id: str) -> str:
        return f"job_status:{job_id}"

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
            db : Session
    ):
        if output_format.lower() not in self.settings.ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail="Format not allowed ")
        
        results = []

        for file in files:
            result = await self._process_single_file(file, output_format, db)
            results.append(result)

        return {"success": True, "jobs": results}

    
    async def _process_single_file(
            self,
            file:UploadFile,
            output_format:str,
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
                "input_path": f"/uploads/{input_filename}",
                "output_path": None,
                "output_format": output_format,
                "error": None
            }

            self.redis.set(self._get_redis_key(job_id),
                           json.dumps(status_data))


            convert_image.delay(job_id,output_format)

            return {
                'job_id': job_id,
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

    async def get_status(self,job_id:str,db:Session):

        redis_key = self._get_redis_key(job_id)
        status_data = self.redis.get(redis_key)

        if status_data:
            print('Got data from redis')
            return json.loads(status_data)
        print('Data missing querried DB')
        # this will only run if not in redis
        job = db.query(ConversionJob).filter(ConversionJob.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "status": job.status,
            "input_path": f"/uploads/{job.input_path}",
            "output_path": f"/converted/{job.output_path}" if job.output_path else None,
            "output_format": job.output_format,
            "error": job.error_message
        }
    
    async def list_jobs(self,db:Session):
        jobs = db.query(ConversionJob).order_by(ConversionJob.created_at.desc()).all()

        return [
            {
                "job_id": job.id,
                "status": job.status,
                "input_path": f"/uploads/{job.input_path}",
                "output_path": f"/converted/{job.output_path}" if job.output_path else None,
                "output_format": job.output_format,
                "created_at": job.created_at,
                "error": job.error_message
            }
            for job in jobs
        ]
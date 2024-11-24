import os
from PIL import Image
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import  Settings
from models import ConversionJob, ConversionStatus
from redis import Redis
import json


settings = Settings()

celery_app = Celery('tasks', broker=f'amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@rabbitmq:5672//')

redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,decode_responses=True)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task
def convert_image(job_id: str, output_format: str,session_id: str):
    db = SessionLocal()
    print('reached inside function convert_image',job_id,output_format)
    try:
      
        job = db.query(ConversionJob).filter(ConversionJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

       
        job.status = ConversionStatus.PROCESSING
        db.commit()

     
        input_path = settings.UPLOAD_DIR / job.input_path
        output_filename = f"{job_id}.{output_format}"
        output_path = settings.CONVERTED_DIR / output_filename

        with Image.open(input_path) as img:
           
            if img.mode == 'RGBA' and output_format.lower() in ['jpeg', 'jpg']:
                img = img.convert('RGB')
            
          
            if output_format.lower() in ['jpeg', 'jpg']:
                img.save(output_path, format=output_format.upper(), optimize=True, quality=85)
            elif output_format.lower() == 'webp':
                img.save(output_path, format='WEBP', lossless=False, quality=85)
            elif output_format.lower() == 'png':
                img.save(output_path, format='PNG', optimize=True)
            else:
                img.save(output_path, format=output_format.upper())

    
        job.status = ConversionStatus.COMPLETED
        job.output_path = str(output_path.relative_to(settings.CONVERTED_DIR))
        job.output_format = output_format
        db.commit()

        status_data = {
                "status": ConversionStatus.COMPLETED,
                "session_id": session_id,
                "job_id":job_id,
                "output_path": f"/converted/{job.output_path}",
                "output_format": output_format,
                "error": None
            }

        redis_client.publish(
            f'task_status_{session_id}',
            json.dumps(status_data)
        )

        return {"status": "success", "output_path": job.output_path}

    except Exception as e:

        status_data = {
                "status": ConversionStatus.FAILED,
                "session_id": session_id,
                "job_id":job_id,
                "output_path": None,
                "output_format": output_format,
                "error": str(e)
            }
        

        redis_client.publish(
            f'task_status_{session_id}',
            json.dumps(status_data)
        )

        job.status = ConversionStatus.FAILED
        job.error_message = str(e)
        db.commit()
        raise e

    finally:
        db.close()
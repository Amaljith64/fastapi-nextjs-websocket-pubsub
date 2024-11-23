# schemas/conversion.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum
from models import ConversionStatus


class JobBase(BaseModel):
    job_id: str
    status: ConversionStatus

class ConversionJob(JobBase):
    filename: str

class ConversionResponse(BaseModel):
    success: bool
    jobs: List[ConversionJob]

class JobStatusResponse(BaseModel):
    status: ConversionStatus
    input_path: str
    output_path: Optional[str]
    output_format: str
    error: Optional[str]

class JobListResponse(JobStatusResponse):
    job_id: str
    created_at: datetime
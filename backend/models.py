from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from database import Base

class ConversionStatus(str, Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

class ConversionJob(Base):
    __tablename__ = 'conversion_jobs'

    id = Column(String, primary_key=True)
    input_path = Column(String, nullable=False)
    output_path = Column(String)
    status = Column(SQLEnum(ConversionStatus), default=ConversionStatus.QUEUED)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    output_format = Column(String) 



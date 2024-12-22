from sqlalchemy import Column, Integer, Float, String, DateTime, func
from .database import Base

class TetrixMetrics(Base):
    __tablename__ = "tetrix_metrics"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now()) 
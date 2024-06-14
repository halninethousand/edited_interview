from sqlalchemy import Column, String, Integer
from .database import Base

class ScreenshotRecord(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True)
    file_path = Column(String)

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ApiUsage(Base):
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)  # '2025-09-06'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL for guests
    request_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
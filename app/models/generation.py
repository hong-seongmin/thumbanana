from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Generation(Base):
    __tablename__ = "generations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL for guests
    input_title = Column(Text, nullable=False)
    input_script_hash = Column(String, nullable=True)
    style_preset = Column(String, nullable=True)
    reference_images_hash = Column(String, nullable=True)
    requested_variants = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cache_key = Column(String, unique=True, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, error
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="generations")
    images = relationship("Image", back_populates="generation", cascade="all, delete-orphan")
    reference_images = relationship("ReferenceImage", back_populates="generation", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    original_path = Column(String, nullable=False)
    filtered_path = Column(String, nullable=True)
    resized_path = Column(String, nullable=True)
    format = Column(String, default="png")
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generation = relationship("Generation", back_populates="images")


class ReferenceImage(Base):
    __tablename__ = "reference_images"
    
    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    source_type = Column(String, nullable=False)  # 'upload' or 'url'
    source_path = Column(String, nullable=False)
    processed_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generation = relationship("Generation", back_populates="reference_images")
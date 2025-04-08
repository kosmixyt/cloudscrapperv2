from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped
from app.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    allowed_origins = relationship("AllowedOrigin", back_populates="owner")
    chrome_sessions = relationship("ChromeSession", back_populates="user")
    requests = relationship("Request", back_populates="user")

class AllowedOrigin(Base):
    __tablename__ = "allowed_origins"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    owner_id : Mapped[int] = Column(Integer, ForeignKey("users.id"))
    owner: Mapped["User"] = relationship("User", back_populates="allowed_origins")
    requests = relationship("Request", back_populates="request_origin")
    disabled = Column(Boolean, default=False)

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String)
    url = Column(String)
    screenShotName = Column(String)
    string_response = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    request_origin_id = Column(Integer, ForeignKey("allowed_origins.id"))
    request_origin = relationship("AllowedOrigin", back_populates="requests")
    chrome_session = relationship("ChromeSession", back_populates="requests",)
    chrome_session_id = Column(Integer, ForeignKey("chrome_sessions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="requests")
    status_code = Column(Integer)



class ChromeSession(Base):
    __tablename__ = "chrome_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    requests = relationship("Request", back_populates="chrome_session")
    proxy = Column(String, nullable=True) # Assuming you have a proxy field
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="chrome_sessions")

class Config:
    from_attributes = True

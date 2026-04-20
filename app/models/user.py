from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Float,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="check_email_format",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = Column(String(255), nullable=True)
    inn = Column(String(12), nullable=True)
    ogrn = Column(String(15), nullable=True)
    kpp = Column(String(9), nullable=True)
    media_outlets = Column(Text, nullable=True)

    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    check_history = relationship(
        "CheckHistory", back_populates="user", cascade="all, delete-orphan"
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    key_type = Column(
        String(50), default="free", nullable=False
    ) 
    max_uses = Column(
        Integer, default=2, nullable=False
    )
    used_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")
    check_history = relationship("CheckHistory", back_populates="api_key")

    @property
    def remaining(self) -> int:
        return max(0, self.max_uses - self.used_count)

    def can_use(self) -> bool:
        return self.is_active and self.remaining > 0

    def increment_use(self):
        self.used_count += 1
        self.last_used_at = datetime.utcnow()


class CheckHistory(Base):
    __tablename__ = "check_history"
    __table_args__ = (
        CheckConstraint(
            "similarity_score >= 0 AND similarity_score <= 100",
            name="check_similarity_score_range",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True, index=True)
    text = Column(Text, nullable=False)
    filename = Column(String(255), nullable=True)
    result = Column(Text, nullable=True)
    similarity_score = Column(Float, default=0.0)
    check_type = Column(
        String(50), default="text", nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="check_history")
    api_key = relationship("APIKey", back_populates="check_history")

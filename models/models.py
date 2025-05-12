from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# database.py에서 생성한 Base import
from database import Base


class UserDB(Base):
    __tablename__ = "users"

    google_id    = Column(String, primary_key=True, index=True)
    email        = Column(String, index=True)
    display_name = Column(String, index=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    last_login   = Column(DateTime(timezone=True), server_default=func.now())
    study_level  = Column(String, default='B')  # 'S', 'A', 'B' 레벨
    
    rec_items     = relationship("RecommendationsDB", back_populates="rec_owner")
    session_items = relationship("SessionDB", back_populates="session_owner")
    log_items     = relationship("UserLogDB", back_populates="log_owner")


class CategoryDB(Base):
    __tablename__ = "categories"

    category_id   = Column(Integer, primary_key=True, index=True)
    name          = Column(String, index=True)
    description   = Column(String)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    questions     = relationship("QuestionDB", back_populates="category")


class QuestionDB(Base):
    __tablename__ = "questions"

    question_id      = Column(Integer, primary_key=True, index=True)
    category_id      = Column(Integer, ForeignKey("categories.category_id"))
    wrong_sentence   = Column(String, index=True)
    right_sentence   = Column(String, index=True)
    wrong_word       = Column(String, index=True)
    right_word       = Column(String, index=True)
    location         = Column(String)
    difficulty_level = Column(Integer)
    explanation      = Column(Text)
    is_active        = Column(Boolean, default=True)
    total_attempts   = Column(Integer, default=0)
    correct_rate     = Column(Float, default=0.0)
    avg_time_spent   = Column(Float, default=0.0)
    dropout_rate     = Column(Float, default=0.0)
    daily_stats      = Column(JSON, default={})
    stats_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    category         = relationship("CategoryDB", back_populates="questions")
    rec_qid_owner    = relationship("RecommendationQuestionsDB", back_populates="rec_qid_items")
    log_question_id  = relationship("UserLogDB", back_populates="log_qid_owner")


class RecommendationsDB(Base):
    __tablename__ = "recommendations"

    rec_id     = Column(String, primary_key=True, index=True)
    google_id  = Column(String, ForeignKey("users.google_id"))
    rec_status = Column(Boolean, default=False)
    rec_type   = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rec_owner = relationship("UserDB", back_populates="rec_items")
    rec_question_owner = relationship("RecommendationQuestionsDB", back_populates="rec_question_items")


class RecommendationQuestionsDB(Base):
    __tablename__ = "recommendationquestions"

    index       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rec_id      = Column(String, ForeignKey("recommendations.rec_id"))
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    order       = Column(Integer, index=True)

    rec_question_items = relationship("RecommendationsDB", back_populates="rec_question_owner")
    rec_qid_items      = relationship("QuestionDB", back_populates="rec_qid_owner")


class SessionDB(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    google_id  = Column(String, ForeignKey("users.google_id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session_owner = relationship("UserDB", back_populates="session_items")


class UserLogDB(Base):
    __tablename__ = "userlogs"

    log_id      = Column(Integer, primary_key=True, index=True)
    google_id   = Column(String, ForeignKey("users.google_id"))
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    correct     = Column(Boolean)
    delaytime   = Column(Float, default=0.0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    log_owner = relationship("UserDB", back_populates="log_items")
    log_qid_owner = relationship("QuestionDB", back_populates="log_question_id")
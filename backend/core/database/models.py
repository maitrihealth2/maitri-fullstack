from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv
import pathlib

_BASE = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(_BASE / ".env")
load_dotenv(_BASE / ".env.local", override=True)

# Expects postgresql://...
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mindbridge.db")

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_reset_on_return": "rollback",
    "pool_timeout": 30,  # Increased timeout for high concurrency
}

if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL pooling
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from sqlalchemy import event

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        from core.logger.terminal import CommandCenter
        # Extract a short preview of the SQL query for the terminal
        short_query = statement.strip().replace('\n', ' ')[:80] + "..."
        action = "READ" if statement.strip().upper().startswith("SELECT") else "WRITE"
        CommandCenter.log_db(action, short_query)
    except Exception:
        pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'comment': 'Core user table storing authentication and base preferences'}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="Unique handle chosen by the user")
    email = Column(String(100), unique=True, index=True, nullable=False, comment="User email for login and recovery")
    hashed_password = Column(String(200), nullable=False)
    preferred_language = Column(String(10), default="en-IN", comment="Language code like en-IN, hi-IN, te-IN, ta-IN")
    created_at = Column(DateTime(timezone=True), default=func.now(), comment="When the user account was created")
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), comment="Last modification timestamp")
    roles = Column(String(100), default="user", nullable=False, comment="Comma-separated roles assigned to the user")
    is_active = Column(Boolean, default=True)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete-orphan")
    journals = relationship("UserJournal", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("CompanionMemory", back_populates="user", cascade="all, delete-orphan")
    persona = relationship("UserPersonaProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    exercise_logs = relationship("ExerciseLog", back_populates="user", cascade="all, delete-orphan")
    onboarding_data = relationship("UserOnboarding", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {'comment': 'Extended personal and therapeutic profile details'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(Text, nullable=True, comment="User-provided biographical context")
    age = Column(Integer, nullable=True)
    preferred_name = Column(String(50), nullable=True, comment="Name the AI should use to address the user")
    therapy_focus = Column(String(100), nullable=True, comment="Main focus area (e.g. anxiety, relationships)")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class UserOnboarding(Base):
    __tablename__ = "user_onboarding"
    __table_args__ = {'comment': 'Initial onboarding preferences and data'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_name = Column(String(50), nullable=True)
    language = Column(String(20), nullable=True)
    conversation_style = Column(String(50), nullable=True)
    communication_mode = Column(String(20), nullable=True)
    initial_emotion = Column(String(50), nullable=True)
    primary_goal = Column(String(100), nullable=True)
    check_in_preference = Column(String(50), nullable=True)
    goals = Column(JSON, nullable=True)
    reasons = Column(JSON, nullable=True)
    version = Column(String(20), default="v1")
    completed_at = Column(DateTime(timezone=True), default=func.now())
    
    user = relationship("User", back_populates="onboarding_data")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {'comment': 'App settings and interface preferences'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme = Column(String(20), default="system", comment="UI Theme (light, dark, system)")
    notifications_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")


class UserGoal(Base):
    __tablename__ = "user_goals"
    __table_args__ = {'comment': 'Therapeutic goals set by the user'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="in_progress", comment="Expected values: in_progress, achieved, abandoned")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    target_date = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="goals")


class UserJournal(Base):
    __tablename__ = "user_journals"
    __table_args__ = {'comment': 'Reflective journal entries written by the user'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    mood = Column(String(30), nullable=True, comment="Mood associated with the entry")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="journals")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {'comment': 'Conversation sessions between user and the companion'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_token = Column(String(100), unique=True, index=True, nullable=False)
    started_at = Column(DateTime(timezone=True), default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    channel = Column(String(20), default="web", comment="Interface used: web, voice, mobile")
    is_crisis_flagged = Column(Boolean, default=False, comment="True if any message in this session triggered crisis detection")
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", order_by="Message.created_at", cascade="all, delete-orphan")
    note = relationship("ConsultationNote", back_populates="session", uselist=False, cascade="all, delete-orphan")
    feedback = relationship("SessionFeedback", back_populates="session", uselist=False, cascade="all, delete-orphan")
    risk_logs = relationship("RiskLog", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'comment': 'Individual messages within a conversation session'}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(20), nullable=False, comment="Speaker role: user, assistant, system")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    language = Column(String(10), default="en-IN")
    is_crisis_flagged = Column(Boolean, default=False)

    # Relationships
    session = relationship("Session", back_populates="messages")
    emotion = relationship("MessageEmotion", back_populates="message", uselist=False, cascade="all, delete-orphan")


class MessageEmotion(Base):
    __tablename__ = "message_emotions"
    __table_args__ = {'comment': 'Emotion classification for a specific message'}
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    emotion_label = Column(String(50), nullable=False)
    score = Column(Float, nullable=False, comment="Confidence score of the emotion model")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    message = relationship("Message", back_populates="emotion")


class CompanionMemory(Base):
    __tablename__ = "companion_memories"
    __table_args__ = {'comment': 'Extracted context that the AI should remember over time'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    memory_type = Column(String(50), nullable=False, comment="Category: core_belief, event, preference, etc.")
    content = Column(Text, nullable=False)
    importance_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="memories")


class UserPersonaProfile(Base):
    """Living psychological persona profile, updated every session.
    Built from onboarding (session 1) and refined through observed behavioral patterns."""
    __tablename__ = "user_persona_profiles"
    __table_args__ = {'comment': 'Living psychological persona — updated each session from behavioral signals'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Onboarding-derived (session 1)
    onboarding_complete = Column(Boolean, default=False, comment="True once first-session discovery is finished")
    initial_presenting_topic = Column(Text, nullable=True, comment="What brought them here in session 1")

    # Communication style (updated over time)
    communication_style = Column(
        String(20), default="unknown",
        comment="expressive | guarded | chatty | quiet | mixed"
    )
    processing_preference = Column(
        String(20), default="unknown",
        comment="venting | problem_solving | both | unknown"
    )
    life_focus_areas = Column(
        JSON, default=list,
        comment="List of key life domains: work, relationships, health, identity, etc."
    )

    # Evolving behavioral signals (updated each session)
    avg_message_length_trend = Column(
        String(20), default="unknown",
        comment="increasing | decreasing | stable — signals engagement/withdrawal"
    )
    language_absolutism_score = Column(
        Float, default=0.0,
        comment="0–1 score of how often user uses absolute language (always/never/nobody)"
    )
    emotional_range = Column(
        JSON, default=list,
        comment="List of emotion labels observed across all sessions"
    )
    dominant_emotion = Column(String(50), nullable=True, comment="Most frequently observed emotion")
    behavioral_notes = Column(
        Text, nullable=True,
        comment="Free-text AI-generated summary of observed patterns, updated each session"
    )

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="persona")


class ExerciseLog(Base):
    """Tracks the full lifecycle of a therapeutic exercise — from suggestion to completion."""
    __tablename__ = "exercise_logs"
    __table_args__ = {'comment': 'Tracks exercise suggestion, engagement, and outcome per session'}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    exercise_type = Column(
        String(30), nullable=False,
        comment="BREATHING | GROUNDING | REFLECTION | BODY_SCAN | COGNITIVE_REFRAME"
    )
    triggered_by = Column(
        String(30), nullable=False,
        comment="analyst_trajectory | analyst_pattern | analyst_keyword | user_requested"
    )
    state = Column(
        String(30), default="suggested",
        comment="suggested | in_progress | awaiting_feedback | completed | dropped"
    )

    pre_emotion = Column(String(50), nullable=True, comment="Emotion label at time of suggestion")
    post_emotion = Column(String(50), nullable=True, comment="Emotion label after exercise completed")
    user_feedback = Column(Text, nullable=True, comment="What the user said after the exercise")

    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", backref="exercise_logs")
    user = relationship("User", back_populates="exercise_logs")


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"
    __table_args__ = {'comment': 'AI-generated summary and insights for a session'}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    key_insights = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    session = relationship("Session", back_populates="note")


class SessionFeedback(Base):
    __tablename__ = "session_feedbacks"
    __table_args__ = {'comment': 'User feedback ratings for a session'}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    rating = Column(Integer, nullable=False, comment="Rating from 1 to 5")
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    session = relationship("Session", back_populates="feedback")


class RiskLog(Base):
    __tablename__ = "risk_logs"
    __table_args__ = {'comment': 'Audit logs of times the system detected high-risk user input'}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    trigger_phrase = Column(Text, nullable=False)
    system_response = Column(Text, nullable=False)
    helpline_shown = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    session = relationship("Session", back_populates="risk_logs")
class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = {'comment': 'User feedback and feature requests'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User")


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = {'comment': 'Feature flags for beta testing and gradual rollouts'}

    id = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String(100), unique=True, index=True, nullable=False)
    is_active_for_all = Column(Boolean, default=False)
    beta_users_only = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

class UserFeatureAccess(Base):
    __tablename__ = "user_feature_access"
    __table_args__ = {'comment': 'Mapping of beta users to specific features'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    feature_name = Column(String(100), ForeignKey("feature_flags.feature_name", ondelete="CASCADE"), index=True, nullable=False)
    granted_at = Column(DateTime(timezone=True), default=func.now())



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete.")

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified.")
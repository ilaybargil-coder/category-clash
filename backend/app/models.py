from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    auth_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    avatar: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    win_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    __table_args__ = (
        CheckConstraint("sender_id != recipient_id", name="ck_friend_requests_distinct_users"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", server_default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        CheckConstraint("user_a_id < user_b_id", name="ck_friendships_normalized_pair"),
        UniqueConstraint("user_a_id", "user_b_id", name="uq_friendships_user_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answers: Mapped[list["ApprovedAnswer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class ServedQuestion(Base):
    __tablename__ = "served_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    served_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DailyResult(Base):
    __tablename__ = "daily_results"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_results_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[date_type] = mapped_column(Date, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"

    date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnswerReport(Base):
    __tablename__ = "answer_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_answer_reports_status",
        ),
        UniqueConstraint(
            "question_id",
            "normalized",
            "reporter_user_id",
            name="uq_answer_reports_question_normalized_reporter",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    raw_text: Mapped[str] = mapped_column(String(200))
    normalized: Mapped[str] = mapped_column(String(200))
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")


class ApprovedAnswer(Base):
    __tablename__ = "approved_answers"
    __table_args__ = (UniqueConstraint("question_id", "canonical"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    canonical: Mapped[str] = mapped_column(String(120))
    semantic_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    question: Mapped["Question"] = relationship(back_populates="answers")
    aliases: Mapped[list["AnswerAlias"]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )


class AnswerAlias(Base):
    __tablename__ = "answer_aliases"
    __table_args__ = (UniqueConstraint("approved_answer_id", "alias"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    approved_answer_id: Mapped[int] = mapped_column(
        ForeignKey("approved_answers.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(120))

    answer: Mapped["ApprovedAnswer"] = relationship(back_populates="aliases")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), index=True)
    player1_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    player2_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    score_p1: Mapped[int] = mapped_column(Integer, default=0)
    score_p2: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    starter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    winner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubmittedAnswer(Base):
    __tablename__ = "submitted_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Server-generated unique id per logical submission; the DB-level unique
    # constraint guarantees one row per submission even under retries.
    submission_id: Mapped[str] = mapped_column(String(32), unique=True)
    client_command_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    raw_text: Mapped[str] = mapped_column(String(200))
    normalized_text: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(20))
    matched_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("approved_answers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

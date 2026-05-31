"""`users` jadvali (R1, R5) — foydalanuvchi (rahbar/ekspert/administrator).

design.md — "users (R1, R5)" jadval ta'rifiga aniq mos keladi.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntType, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import (
        DeviceToken,
        PasswordResetCode,
        RefreshToken,
    )
    from app.models.expert import ExpertReview
    from app.models.feedback import Feedback
    from app.models.portfolio import Portfolio
    from app.models.reference import Organization, Region, Role
    from app.models.result import TestResult
    from app.models.session import TestSession


class User(TimestampMixin, Base):
    """Tizim foydalanuvchisi — hisob identifikatori telefon raqami (R5.4)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "experience_years >= 0 AND experience_years <= 60",
            name="experience_years_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True)
    # 1–200 belgi (R1.1)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # +998, jami 13 belgi; o'zgarmas hisob identifikatori (R1.6, R5.4)
    phone: Mapped[str] = mapped_column(String(13), nullable=False, unique=True)
    # xeshlangan parol (R1.4, R17.1)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id"), nullable=True
    )

    position: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # ish staji 0–60 (R5.3)
    experience_years: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    education_level: Mapped[str | None] = mapped_column(String(200), nullable=True)
    qualification_courses: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificates: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # push yoqilgani (R16.5)
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # login bloklash hisoblagichi (R2.7)
    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    role: Mapped["Role"] = relationship(back_populates="users")
    organization: Mapped["Organization | None"] = relationship(
        back_populates="users"
    )
    region: Mapped["Region | None"] = relationship(back_populates="users")

    test_sessions: Mapped[list["TestSession"]] = relationship(
        back_populates="user"
    )
    test_results: Mapped[list["TestResult"]] = relationship(back_populates="user")
    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user"
    )
    password_reset_codes: Mapped[list["PasswordResetCode"]] = relationship(
        back_populates="user"
    )
    device_tokens: Mapped[list["DeviceToken"]] = relationship(
        back_populates="user"
    )

    # Ekspert sharhlari: foydalanuvchi ekspert yoki baholanuvchi (rahbar) bo'lishi mumkin.
    reviews_given: Mapped[list["ExpertReview"]] = relationship(
        back_populates="expert",
        foreign_keys="ExpertReview.expert_id",
    )
    reviews_received: Mapped[list["ExpertReview"]] = relationship(
        back_populates="leader",
        foreign_keys="ExpertReview.leader_id",
    )

    feedbacks_received: Mapped[list["Feedback"]] = relationship(
        back_populates="target_user",
        foreign_keys="Feedback.target_user_id",
    )


__all__ = ["User"]

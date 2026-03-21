"""Add review author rule table

Revision ID: c1f3d2a6b4e5
Revises: 8e22df58cff8
Create Date: 2026-03-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

import paihub
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f3d2a6b4e5"
down_revision: str | Sequence[str] | None = "8e22df58cff8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "review_author_rule",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=True),
        sa.Column("site_key", paihub.utils.sql_types.SiteKey(), nullable=True),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "action",
            sa.Enum("AUTO_REJECT", "AUTO_PASS", name="reviewauthorruleaction"),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("create_by", sa.Integer(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("update_by", sa.Integer(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["work_id"], ["work.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id", "site_key", "author_id", name="uq_review_author_rule_work_site_author"),
    )
    op.create_index(
        "ix_review_author_rule_work_site_action",
        "review_author_rule",
        ["work_id", "site_key", "action"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_review_author_rule_work_site_action", table_name="review_author_rule")
    op.drop_table("review_author_rule")

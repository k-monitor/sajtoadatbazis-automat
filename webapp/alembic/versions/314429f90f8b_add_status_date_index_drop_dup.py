"""add_status_date_index_drop_dup

Adds an equality-first compound to serve get_articles' match_query with a
usable date range, and drops a duplicate (group_id, id) index left from a
prior ad-hoc migration.

The existing idx_news_positive_negative (classification_label, processing_step,
annotation_label, newspaper_id) lets MySQL match the 3 status equalities but
cannot use article_date (4th column is newspaper_id, not always filtered).
This forces a scan of every row matching the status — ~180k for a 6-month
window. The new index ends with article_date, making the date BETWEEN a
usable index range.

Also drops idx_news_group_min_id which duplicates idx_news_grouped_lookup.

Revision ID: 314429f90f8b
Revises: 4907e74c1344
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "314429f90f8b"
down_revision: Union[str, Sequence[str], None] = "4907e74c1344"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_news_status_date",
        "autokmdb_news",
        ["classification_label", "processing_step", "annotation_label", "article_date"],
    )
    op.drop_index("idx_news_group_min_id", table_name="autokmdb_news")


def downgrade() -> None:
    op.drop_index("idx_news_status_date", table_name="autokmdb_news")
    op.create_index(
        "idx_news_group_min_id",
        "autokmdb_news",
        ["group_id", "id"],
    )

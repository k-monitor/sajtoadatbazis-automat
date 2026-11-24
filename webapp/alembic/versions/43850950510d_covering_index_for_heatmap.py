"""covering_index_for_heatmap

Replaces idx_news_date_status_search with a tighter index that fully covers
the get_articles_by_day SELECT list. The old index lacked negative_reason,
so MySQL fell back to a full table scan (1.9M rows, 321s) for the heatmap.

The new index includes every column the heatmap query references so MySQL
can do an index-only scan with no heap reads. article_date leads so the
GROUP BY DATE(article_date) flows in index order without filesort.

Also drops idx_news_date_status_search since the new index is a strict
improvement.

Revision ID: 43850950510d
Revises: 314429f90f8b
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "43850950510d"
down_revision: Union[str, Sequence[str], None] = "314429f90f8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_news_heatmap",
        "autokmdb_news",
        ["article_date", "processing_step", "annotation_label",
         "classification_label", "negative_reason", "skip_reason"],
    )
    op.drop_index("idx_news_date_status_search", table_name="autokmdb_news")


def downgrade() -> None:
    op.create_index(
        "idx_news_date_status_search",
        "autokmdb_news",
        ["article_date", "processing_step", "classification_label",
         "annotation_label", "skip_reason", "newspaper_id", "group_id"],
    )
    op.drop_index("idx_news_heatmap", table_name="autokmdb_news")

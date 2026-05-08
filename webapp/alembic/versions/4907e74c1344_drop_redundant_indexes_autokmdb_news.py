"""drop_redundant_indexes_autokmdb_news

Reduces autokmdb_news from ~48 indexes to 9 keepers.

Background: indexes accumulated over time as ad-hoc fixes for slow queries.
Slow query log analysis showed write contention (slow COMMITs, slow UPDATEs)
caused by every write rewriting all index B-trees. Many indexes never get
used because:
  - leading columns have very low cardinality (classification_label, etc.)
  - they were attempts to index an OR-pattern that no index can serve
  - prefix indexes on title/description don't help LIKE '%term%' searches
  - several are exact duplicates of others or covered by PRIMARY

Keepers (9):
  PRIMARY, fk_mod_id, idx_news_url, idx_autokmdb_news_source_url_search,
  idx_news_sorting, idx_autokmdb_news_newspaper_date, idx_news_grouped_lookup,
  idx_news_positive_negative, idx_autokmdb_news_processing_annotation

Run this off-peak. MySQL 5.5 DDL is not online; each DROP INDEX briefly
locks the table.

Revision ID: 4907e74c1344
Revises: e7aee212c233
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op


revision: str = "4907e74c1344"
down_revision: Union[str, Sequence[str], None] = "e7aee212c233"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES_TO_DROP = [
    # Duplicates of keepers
    "idx_news_group_min_lookup",            # dup of idx_news_grouped_lookup
    "idx_autokmdb_news_group_operations",   # dup of idx_news_grouped_lookup
    "idx_autokmdb_news_clean_url_search",   # dup of idx_news_url
    "idx_news_newspaper_id",                # covered by idx_autokmdb_news_newspaper_date

    # Covered by PRIMARY
    "idx_autokmdb_news_id_lookup",
    "idx_article_lookup",
    "idx_autokmdb_news_id_news_id_lookup",

    # Single-col / narrow, covered by composites we keep
    "idx_autokmdb_news_article_date",
    "idx_autokmdb_news_date_range",

    # Low-cardinality leading column or prefix-redundant with keepers
    "idx_news_mixed",
    "idx_news_processing_all",
    "idx_autokmdb_news_classification_step",
    "idx_autokmdb_news_mixed_status",
    "idx_autokmdb_news_compound",
    "idx_autokmdb_news_search_complex",
    "idx_autokmdb_news_search_optimized",

    # Function-on-column makes these unusable (COALESCE(skip_reason, 0) = 0)
    "idx_skip_reason_filter",

    # LIKE '%term%' searches can't use prefix indexes
    "idx_autokmdb_news_title_search",
    "idx_autokmdb_news_description_search",

    # Wide indexes with trailing prefix string cols — pure write tax
    "idx_search_mixed",
    "idx_search_positive",
    "idx_search_negative",
    "idx_search_processing",
    "idx_search_all",

    # Attempts to serve the unindexable OR pattern in the listing query
    "idx_grouped_main",
    "idx_ungrouped_mixed",
    "idx_ungrouped_positive",
    "idx_ungrouped_negative",
    "idx_ungrouped_processing",
    "idx_ungrouped_all",
    "idx_qualifying_groups_mixed",
    "idx_qualifying_groups_positive",
    "idx_qualifying_groups_negative",
    "idx_qualifying_groups_processing",
    "idx_qualifying_groups_all",
    "idx_negative_groups_fast",
    "idx_negative_ungrouped_fast",
    "idx_negative_covering_wide",
    "idx_bulk_grouped_articles",
]


def upgrade() -> None:
    for idx in INDEXES_TO_DROP:
        op.drop_index(idx, table_name="autokmdb_news")


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported. Recreating these indexes would take a long "
        "time and reintroduce the write contention this migration was designed "
        "to fix. If you need to roll back, restore from a pre-migration backup."
    )

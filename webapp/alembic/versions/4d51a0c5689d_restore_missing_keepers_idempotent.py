"""restore_missing_keepers_idempotent

Restores two indexes the cleanup migration (4907e74c1344) treated as keepers
but that turned out to be missing on production — pre-alembic schema drift
between dev and prod. On dev these already exist, so the migration skips
them; on prod it creates them.

  - idx_news_grouped_lookup (group_id, id): used by grouped-article queries
    (MIN(id) per group_id lookups).
  - idx_news_positive_negative (classification_label, processing_step,
    annotation_label, newspaper_id): the newspaper-aware complement to
    idx_news_status_date added in 314429f90f8b. Without it, listing queries
    that filter by status + newspaper but no date have to scan.

Idempotent via index-existence check so the same revision is safe on both
environments.

Revision ID: 4d51a0c5689d
Revises: 43850950510d
Create Date: 2026-05-08

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "4d51a0c5689d"
down_revision: Union[str, Sequence[str], None] = "43850950510d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES_TO_RESTORE = [
    ("idx_news_grouped_lookup", ["group_id", "id"]),
    (
        "idx_news_positive_negative",
        ["classification_label", "processing_step", "annotation_label", "newspaper_id"],
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = {ix["name"] for ix in inspect(bind).get_indexes("autokmdb_news")}
    for name, cols in INDEXES_TO_RESTORE:
        if name not in existing:
            op.create_index(name, "autokmdb_news", cols)


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported. These indexes are keepers per 4907e74c1344; "
        "dropping them would degrade the listing and grouped-article queries."
    )

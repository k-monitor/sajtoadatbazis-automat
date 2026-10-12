"""add_entity_descriptions

Table for the LLM-generated description suggestions of KMDB entities (persons,
institutions, files, newspapers). A row is created when someone queues an
entity on the /descriptions page (status 'queued'), the DescriptionProcessor
fills in the suggestion ('review' or 'error'), and a reviewer accepts or
rejects it. Accepting writes the text to both the teaser and the bodytext of
the entity in the KMDB, their previous HTML is kept in old_teaser and
old_bodytext as a backup.

mod_time is the only TIMESTAMP with a CURRENT_TIMESTAMP default because
MySQL 5.5 allows just one per table; cre_time is set explicitly on insert.

Revision ID: a3c1f7d92b10
Revises: 4d51a0c5689d
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a3c1f7d92b10"
down_revision: Union[str, Sequence[str], None] = "4d51a0c5689d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE autokmdb_entity_descriptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            entity_type VARCHAR(16) NOT NULL,
            entity_id INT NOT NULL,
            entity_name VARCHAR(512) NOT NULL,
            status VARCHAR(16) NOT NULL,
            suggestion MEDIUMTEXT,
            final_description MEDIUMTEXT,
            old_teaser MEDIUMTEXT,
            old_bodytext MEDIUMTEXT,
            sources MEDIUMTEXT,
            prompt MEDIUMTEXT,
            model VARCHAR(64),
            error TEXT,
            prompt_tokens INT,
            response_tokens INT,
            thinking_tokens INT,
            cre_id INT,
            mod_id INT,
            cre_time DATETIME NOT NULL,
            mod_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_entity_descriptions_status (status, cre_time),
            KEY idx_entity_descriptions_entity (entity_type, entity_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def downgrade() -> None:
    op.drop_table("autokmdb_entity_descriptions")

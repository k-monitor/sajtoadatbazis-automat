-- ALTER TABLE autokmdb_news ADD group_id INT;

CREATE TABLE autokmdb_news_groups (
    group_id INT NOT NULL,
    autokmdb_news_id INT NOT NULL,
    is_main BOOL NOT NULL
);

ALTER TABLE autokmdb_news_groups ADD PRIMARY KEY (group_id, autokmdb_news_id);

ALTER TABLE autokmdb_news_groups ADD CONSTRAINT unique_article_per_group UNIQUE (autokmdb_news_id);

ALTER TABLE autokmdb_news_groups ADD CONSTRAINT fk_news_to_groups FOREIGN KEY (autokmdb_news_id) REFERENCES autokmdb_news(id) ON DELETE CASCADE;

CREATE INDEX idx_news_groups_news ON autokmdb_news_groups(autokmdb_news_id);

CREATE INDEX idx_news_groups_group ON autokmdb_news_groups(group_id);

-- mysql -h 127.0.0.1 -P 9999 -u autokmdb -p autokmdb --skip_ssl < add_article_groups.sql

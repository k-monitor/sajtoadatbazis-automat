ALTER TABLE autokmdb_news DROP INDEX idx_news_sorting;
CREATE INDEX idx_news_sorting ON autokmdb_news (source, article_date);

-- ALTER TABLE autokmdb_news DROP INDEX idx_news_filtering;
CREATE INDEX idx_news_combined ON autokmdb_news (classification_label, annotation_label, skip_reason, newspaper_id, processing_step, cre_time, article_date);

ALTER TABLE autokmdb_news MODIFY mod_id INT(11) NOT NULL
ALTER TABLE autokmdb_news ADD CONSTRAINT fk_mod_id FOREIGN KEY (mod_id) REFERENCES users(user_id);
CREATE INDEX idx_news_combined ON autokmdb_news (classification_label, annotation_label, skip_reason, newspaper_id, processing_step, cre_time, article_date);
ALTER TABLE autokmdb_news DROP INDEX idx_news_filtering;
ALTER TABLE autokmdb_news ADD CONSTRAINT fk_mod_id FOREIGN KEY (mod_id) REFERENCES users(user_id);
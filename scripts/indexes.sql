CREATE INDEX idx_news_filtering ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason, newspaper_id);
CREATE INDEX idx_news_sorting ON autokmdb_news (source, mod_time);
CREATE FULLTEXT INDEX idx_news_fulltext_search ON autokmdb_news (title, description, source_url);

CREATE INDEX idx_persons_news_id ON autokmdb_persons (autokmdb_news_id);
CREATE INDEX idx_institutions_news_id ON autokmdb_institutions (autokmdb_news_id);
CREATE INDEX idx_places_news_id ON autokmdb_places (autokmdb_news_id);
CREATE INDEX idx_others_news_id ON autokmdb_others (autokmdb_news_id);

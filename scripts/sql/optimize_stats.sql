CREATE INDEX idx_autokmdb_news_article_date ON autokmdb_news (article_date);
CREATE INDEX idx_autokmdb_news_processing_annotation ON autokmdb_news (processing_step, annotation_label, negative_reason);
CREATE INDEX idx_autokmdb_news_classification_step ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason);
CREATE INDEX idx_autokmdb_news_newspaper_date ON autokmdb_news (newspaper_id, article_date);
CREATE INDEX idx_autokmdb_news_compound ON autokmdb_news (article_date, newspaper_id, processing_step, annotation_label, classification_label);

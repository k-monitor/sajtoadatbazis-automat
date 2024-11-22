ALTER TABLE autokmdb_news DROP INDEX idx_news_sorting;
CREATE INDEX idx_news_sorting ON autokmdb_news (source, article_date);

-- Drop existing less optimal indexes
DROP INDEX idx_news_combined ON autokmdb_news;

-- Indexes for the most common status queries with date range
-- For "mixed" status: classification_label = 1 AND processing_step = 4 AND annotation_label IS NULL AND skip_reason = 0
CREATE INDEX idx_news_mixed_status ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason, article_date, newspaper_id, source, id);

-- For "positive" status: processing_step = 5 AND annotation_label = 1
CREATE INDEX idx_news_positive_status ON autokmdb_news (processing_step, annotation_label, article_date, newspaper_id, id);

-- For "negative" status: processing_step = 5 AND annotation_label = 0  
CREATE INDEX idx_news_negative_status ON autokmdb_news (processing_step, annotation_label, article_date, newspaper_id, source, id);

-- For "processing" status: processing_step < 4
CREATE INDEX idx_news_processing_status ON autokmdb_news (processing_step, article_date, newspaper_id, source, id);

-- For "all" status and general queries
CREATE INDEX idx_news_all_status ON autokmdb_news (article_date, newspaper_id, processing_step, source, id);

-- Index specifically for grouping operations
CREATE INDEX idx_news_group_operations ON autokmdb_news (group_id, id);

-- Index for search queries (title, description, source_url LIKE)
-- Note: FULLTEXT index already exists, but add regular index for newspaper filtering with search
CREATE INDEX idx_news_search_filter ON autokmdb_news (newspaper_id, article_date, id);

-- Index for skip_reason filtering
CREATE INDEX idx_news_skip_reason ON autokmdb_news (skip_reason, article_date, newspaper_id, id);

-- Optimize the grouped articles lookup
CREATE INDEX idx_news_grouped_lookup ON autokmdb_news (group_id, id);

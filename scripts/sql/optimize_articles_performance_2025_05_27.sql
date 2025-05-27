-- Drop existing less optimal indexes
DROP INDEX idx_news_combined ON autokmdb_news;
DROP INDEX idx_news_mixed_status ON autokmdb_news;
DROP INDEX idx_news_positive_status ON autokmdb_news;
DROP INDEX idx_news_negative_status ON autokmdb_news;
DROP INDEX idx_news_processing_status ON autokmdb_news;
DROP INDEX idx_news_all_status ON autokmdb_news;
DROP INDEX idx_news_group_operations ON autokmdb_news;
DROP INDEX idx_news_search_filter ON autokmdb_news;
DROP INDEX idx_news_skip_reason ON autokmdb_news;
DROP INDEX idx_news_group_filtering ON autokmdb_news;
DROP INDEX idx_news_simple_mixed ON autokmdb_news;
DROP INDEX idx_news_simple_positive ON autokmdb_news;
DROP INDEX idx_news_simple_negative ON autokmdb_news;
DROP INDEX idx_news_simple_processing ON autokmdb_news;
DROP INDEX idx_news_simple_all ON autokmdb_news;
DROP INDEX idx_news_group_min ON autokmdb_news;

-- Optimized indexes for the qualifying groups query (first step)
-- This covers the WHERE clause in the qualifying_groups_query
--todo
CREATE INDEX idx_qualifying_groups_mixed ON autokmdb_news (group_id, classification_label, processing_step, annotation_label, skip_reason, newspaper_id, article_date);
CREATE INDEX idx_qualifying_groups_positive ON autokmdb_news (group_id, processing_step, annotation_label, newspaper_id, article_date);
CREATE INDEX idx_qualifying_groups_negative ON autokmdb_news (group_id, processing_step, annotation_label, newspaper_id, article_date);
CREATE INDEX idx_qualifying_groups_processing ON autokmdb_news (group_id, processing_step, newspaper_id, article_date);
CREATE INDEX idx_qualifying_groups_all ON autokmdb_news (group_id, processing_step, newspaper_id, article_date);

-- For the main query - covers the MIN(n3.id) subquery
CREATE INDEX idx_news_group_min_lookup ON autokmdb_news (group_id, id);

-- For the main query WHERE clause - ungrouped articles (group_id IS NULL)
CREATE INDEX idx_ungrouped_mixed ON autokmdb_news (group_id, classification_label, processing_step, annotation_label, skip_reason, newspaper_id, article_date, source, id);
CREATE INDEX idx_ungrouped_positive ON autokmdb_news (group_id, processing_step, annotation_label, newspaper_id, article_date, id);
CREATE INDEX idx_ungrouped_negative ON autokmdb_news (group_id, processing_step, annotation_label, newspaper_id, article_date, source, id);
CREATE INDEX idx_ungrouped_processing ON autokmdb_news (group_id, processing_step, newspaper_id, article_date, source, id);
CREATE INDEX idx_ungrouped_all ON autokmdb_news (group_id, processing_step, newspaper_id, article_date, source, id);

-- For the main query WHERE clause - grouped articles (group_id IS NOT NULL)
CREATE INDEX idx_grouped_main ON autokmdb_news (group_id, id, article_date, source);

-- Keep the grouped articles lookup index
CREATE INDEX idx_news_grouped_lookup ON autokmdb_news (group_id, id);

-- Add search support indexes (when search_query != "%%")
CREATE INDEX idx_search_mixed ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason, newspaper_id, article_date, title, description, source_url);
CREATE INDEX idx_search_positive ON autokmdb_news (processing_step, annotation_label, newspaper_id, article_date, title, description, source_url);
CREATE INDEX idx_search_negative ON autokmdb_news (processing_step, annotation_label, newspaper_id, article_date, title, description, source_url);
CREATE INDEX idx_search_processing ON autokmdb_news (processing_step, newspaper_id, article_date, title, description, source_url);
CREATE INDEX idx_search_all ON autokmdb_news (processing_step, newspaper_id, article_date, title, description, source_url);

-- Skip reason filtering
CREATE INDEX idx_skip_reason_filter ON autokmdb_news (skip_reason, newspaper_id, article_date, processing_step);
-- Optimization script for search queries in get_articles
-- Date: 2025-12-09
-- Database: MySQL 5.5.58

-- IMPORTANT: Run these one at a time and monitor for lock issues on production
-- Consider running during low-traffic periods

-- Step 1: Index for group resolution (finding MIN(id) per group_id)
-- This is crucial for the correlated subquery performance
-- Check if exists first: SHOW INDEX FROM autokmdb_news WHERE Key_name = 'idx_news_group_min_id';
CREATE INDEX idx_news_group_min_id ON autokmdb_news (group_id, id);

-- Step 2: Covering index for search with common filter columns
-- Putting date first helps when filtering by date range (common case)
CREATE INDEX idx_news_date_status_search ON autokmdb_news (
    article_date,
    processing_step,
    classification_label, 
    annotation_label,
    skip_reason,
    newspaper_id,
    group_id
);

-- Step 3: Index optimized for sorting with source priority
CREATE INDEX idx_news_sort_source_date ON autokmdb_news (source DESC, article_date DESC, id);

-- Step 4: Index for the grouped articles bulk fetch query
-- This is a covering index for the grouped articles query
CREATE INDEX idx_news_group_fetch ON autokmdb_news (
    group_id, 
    id, 
    clean_url(100), 
    title(100), 
    article_date, 
    newspaper_name
);

-- OPTIONAL: For MySQL 5.6+ only - FULLTEXT index for text search
-- Uncomment if you have MySQL 5.6+ or if table is MyISAM
-- ALTER TABLE autokmdb_news ADD FULLTEXT INDEX idx_news_fulltext (title, description);

-- ALTERNATIVE OPTIMIZATION: If FULLTEXT is not available, consider:
-- 1. Application-level search caching (Redis/Memcached)
-- 2. External search engine (Elasticsearch, Meilisearch)
-- 3. Limiting search to specific date ranges
-- 4. Using prefix-only searches (LIKE 'term%') when possible

-- Query analysis commands (run these to verify index usage):
-- EXPLAIN SELECT ... your query ...
-- SHOW PROFILE FOR QUERY 1;

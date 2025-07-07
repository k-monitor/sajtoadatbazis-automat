-- Alternative approach without FULLTEXT indexes for better LIKE performance

-- Composite index for common filtering patterns (order matters for query optimization)
CREATE INDEX idx_autokmdb_news_search_optimized ON autokmdb_news (
    processing_step, 
    classification_label,
    annotation_label, 
    skip_reason, 
    newspaper_id, 
    article_date
);

-- Optimized indexes for text searches using prefixes
CREATE INDEX idx_autokmdb_news_title_search ON autokmdb_news (title(100));
CREATE INDEX idx_autokmdb_news_description_search ON autokmdb_news (description(200));
CREATE INDEX idx_autokmdb_news_source_url_search ON autokmdb_news (source_url(150));
CREATE INDEX idx_autokmdb_news_clean_url_search ON autokmdb_news (clean_url(150));

-- Index for grouping operations
CREATE INDEX idx_autokmdb_news_group_operations ON autokmdb_news (group_id, id);

-- Index for date range queries with processing step
CREATE INDEX idx_autokmdb_news_date_range ON autokmdb_news (article_date, processing_step);

-- Composite index specifically for mixed status queries
CREATE INDEX idx_autokmdb_news_mixed_status ON autokmdb_news (
    classification_label, 
    processing_step, 
    annotation_label, 
    skip_reason
);

-- Index for newspaper filtering with date
CREATE INDEX idx_autokmdb_news_newspaper_date ON autokmdb_news (newspaper_id, article_date);

-- Multi-column index for complex search queries
CREATE INDEX idx_autokmdb_news_search_complex ON autokmdb_news (
    newspaper_id,
    processing_step,
    article_date,
    classification_label
);

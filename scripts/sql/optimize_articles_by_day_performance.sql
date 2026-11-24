-- Optimization for get_articles_by_day query performance

-- Drop the previous less optimal indexes
DROP INDEX IF EXISTS idx_articles_by_day_covering ON autokmdb_news;
DROP INDEX IF EXISTS idx_articles_by_day_no_newspaper ON autokmdb_news;

-- Optimized composite indexes for get_articles_by_day query performance
-- These indexes are ordered to support the most selective conditions first

-- For positive articles: processing_step = 5 AND annotation_label = 1
CREATE INDEX idx_articles_by_day_positive ON autokmdb_news (
    processing_step, 
    annotation_label,
    article_date, 
    newspaper_id
);

-- For negative articles: processing_step = 5 AND annotation_label = 0  
CREATE INDEX idx_articles_by_day_negative ON autokmdb_news (
    processing_step, 
    annotation_label,
    article_date, 
    newspaper_id
);

-- For todo articles: classification_label = 1 AND processing_step = 4 AND annotation_label IS NULL
CREATE INDEX idx_articles_by_day_todo ON autokmdb_news (
    classification_label, 
    processing_step, 
    annotation_label,
    skip_reason,
    article_date,
    newspaper_id
);

-- General date-first index for the initial date query
CREATE INDEX idx_articles_by_day_dates ON autokmdb_news (
    article_date, 
    newspaper_id
);

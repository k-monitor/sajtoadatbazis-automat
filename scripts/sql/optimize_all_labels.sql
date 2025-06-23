-- Indexes for the get_all() function and its variants
-- These are missing from your existing indexes
CREATE INDEX idx_news_persons_status_name ON news_persons(status, name);
CREATE INDEX idx_news_institutions_status_name ON news_institutions(status, name);
CREATE INDEX idx_news_places_status_name ON news_places(status, name_hu);
CREATE INDEX idx_news_others_status_name ON news_others(status, name_hu);
CREATE INDEX idx_news_files_status_name ON news_files(status, name_hu);

-- Indexes for the get_all_freq() function and its variants
-- These are missing from your existing indexes
CREATE INDEX idx_news_persons_freq ON news_persons(status, person_id, name);
CREATE INDEX idx_news_institutions_freq ON news_institutions(status, institution_id, name);
CREATE INDEX idx_news_places_freq ON news_places(status, place_id, name_hu);
CREATE INDEX idx_news_others_freq ON news_others(status, other_id, name_hu);

-- Indexes for the link table JOINs in get_all_freq()
-- These are missing from your existing indexes
CREATE INDEX idx_news_persons_link_person_id ON news_persons_link(person_id);
CREATE INDEX idx_news_institutions_link_institution_id ON news_institutions_link(institution_id);
CREATE INDEX idx_news_places_link_place_id ON news_places_link(place_id);
CREATE INDEX idx_news_others_link_other_id ON news_others_link(other_id);

-- Index for get_all_newspapers() LEFT JOIN optimization
-- This specific combination is missing
CREATE INDEX idx_newspapers_articles_count ON news_newspapers(status, newspaper_id, name, rss_url);

-- Index for get_places_alias() JOIN optimization
-- This is missing from your existing indexes
CREATE INDEX idx_autokmdb_alias_place_join ON autokmdb_alias_place(place_id);

-- Composite index for better KMDB entity lookups in get_article()
-- These specific combinations are missing
CREATE INDEX idx_news_persons_link_lookup ON news_persons_link(news_id, person_id);
CREATE INDEX idx_news_institutions_link_lookup ON news_institutions_link(news_id, institution_id);
CREATE INDEX idx_news_places_link_lookup ON news_places_link(news_id, place_id);
CREATE INDEX idx_news_others_link_lookup ON news_others_link(news_id, other_id);

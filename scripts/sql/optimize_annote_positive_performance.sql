-- Indexes for annote_positive function optimization

-- For news_id lookup in autokmdb_news
CREATE INDEX idx_autokmdb_news_id_lookup ON autokmdb_news (id, news_id);

-- For autokmdb entity updates
CREATE INDEX idx_autokmdb_persons_id ON autokmdb_persons (id);
CREATE INDEX idx_autokmdb_institutions_id ON autokmdb_institutions (id);
CREATE INDEX idx_autokmdb_places_id ON autokmdb_places (id);

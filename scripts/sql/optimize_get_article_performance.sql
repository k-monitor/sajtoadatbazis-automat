-- Indexes for the main get_article query with JOINs

-- Primary lookup index for the article
CREATE INDEX idx_article_lookup ON autokmdb_news (id);

-- Indexes for entity JOINs
CREATE INDEX idx_persons_article_join ON autokmdb_persons (autokmdb_news_id, id);
CREATE INDEX idx_institutions_article_join ON autokmdb_institutions (autokmdb_news_id, id);  
CREATE INDEX idx_places_article_join ON autokmdb_places (autokmdb_news_id, id);
CREATE INDEX idx_others_article_join ON autokmdb_others (autokmdb_news_id, id);

-- Covering indexes for entity data to avoid table lookups
CREATE INDEX idx_persons_covering ON autokmdb_persons (autokmdb_news_id, id, name, person_id, person_name, classification_score, classification_label, annotation_label, found_name, found_position);
CREATE INDEX idx_institutions_covering ON autokmdb_institutions (autokmdb_news_id, id, name, institution_id, institution_name, classification_score, classification_label, annotation_label, found_name, found_position);
CREATE INDEX idx_places_covering ON autokmdb_places (autokmdb_news_id, id, name, place_id, place_name, classification_score, classification_label, annotation_label, found_name, found_position);
CREATE INDEX idx_others_covering ON autokmdb_others (autokmdb_news_id, id, name, other_id, classification_score, classification_label, annotation_label);

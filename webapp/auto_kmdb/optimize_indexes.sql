-- Index for autokmdb_news id lookup in annote_positive function optimization - improves the initial news_id lookup
CREATE INDEX idx_autokmdb_news_id_news_id_lookup ON autokmdb_news (id, news_id);

-- Additional annote_positive optimization indexes

-- Index for news_persons name lookups during entity existence checks  
CREATE INDEX idx_news_persons_name_lookup ON news_persons (name);

-- Index for news_institutions name lookups during entity existence checks  
CREATE INDEX idx_news_institutions_name_lookup ON news_institutions (name);

-- Index for news_places parent_id lookups
CREATE INDEX idx_news_places_parent_lookup ON news_places (place_id, parent_id);

-- Index for news_persons_link bulk operations
CREATE INDEX idx_news_persons_link_bulk ON news_persons_link (news_id, person_id);

-- Index for news_institutions_link bulk operations
CREATE INDEX idx_news_institutions_link_bulk ON news_institutions_link (news_id, institution_id);

-- Index for news_places_link bulk operations
CREATE INDEX idx_news_places_link_bulk ON news_places_link (news_id, place_id);

-- Index for news_others_link bulk operations
CREATE INDEX idx_news_others_link_bulk ON news_others_link (news_id, other_id);

-- Index for news_files_link bulk operations
CREATE INDEX idx_news_files_link_bulk ON news_files_link (news_id, file_id);

-- Index for autokmdb_persons annotation updates
CREATE INDEX idx_autokmdb_persons_annotation_update ON autokmdb_persons (id, annotation_label);

-- Index for autokmdb_institutions annotation updates
CREATE INDEX idx_autokmdb_institutions_annotation_update ON autokmdb_institutions (id, annotation_label);

-- Index for autokmdb_places annotation updates
CREATE INDEX idx_autokmdb_places_annotation_update ON autokmdb_places (id, annotation_label);

-- Index for news_lang table for updates and inserts
CREATE INDEX idx_news_lang_news_id ON news_lang (news_id);

-- Index for news_newspapers_link operations
CREATE INDEX idx_news_newspapers_link_news_id ON news_newspapers_link (news_id);

-- Index for news_categories_link operations
CREATE INDEX idx_news_categories_link_news_id ON news_categories_link (news_id);

-- Index for seo_urls_data operations
CREATE INDEX idx_seo_urls_data_item_id ON seo_urls_data (item_id, modul);

-- Index for news_tags operations
CREATE INDEX idx_news_tags_news_id ON news_tags (news_id);

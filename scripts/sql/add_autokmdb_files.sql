CREATE TABLE autokmdb_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT NOT NULL,
    files_id INT NOT NULL,
    name VARCHAR(512) NOT NULL,
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
)
CHARACTER SET utf8 COLLATE utf8_general_ci;

CREATE INDEX idx_files_news_id ON autokmdb_files (autokmdb_news_id);
CREATE INDEX idx_files_status_name ON news_files (status, name_hu);
CREATE INDEX idx_files_article_join ON autokmdb_files (autokmdb_news_id, id);
CREATE INDEX idx_files_covering ON autokmdb_files (autokmdb_news_id, id, name, files_id, classification_score, classification_label, annotation_label);
CREATE INDEX idx_news_files_link_lookup ON news_files_link(news_id, file_id);
CREATE INDEX idx_news_files_link_file_id ON news_files_link(file_id);
CREATE INDEX idx_news_files_freq ON news_files(status, file_id, name_hu);

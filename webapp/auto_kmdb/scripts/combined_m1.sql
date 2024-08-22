CREATE TABLE autokmdb_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT,
    source INT NOT NULL,
    source_url VARCHAR(512) NOT NULL,
    clean_url VARCHAR(512) NOT NULL,
    newspaper_name VARCHAR(512) NOT NULL,
    newspaper_id INT NOT NULL,
    text MEDIUMTEXT,
    title VARCHAR(512),
    author VARCHAR(512),
    description VARCHAR(1024),
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    skip_reason INT,
    processing_step INT NOT NULL,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
)
CHARACTER SET utf8 COLLATE utf8_general_ci;

CREATE TABLE autokmdb_persons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    person_name VARCHAR(512),
    person_id INT,
    found_name VARCHAR(512) NOT NULL,
    found_position INT NOT NULL,
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

CREATE TABLE autokmdb_institutions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    institution_name VARCHAR(512),
    institution_id INT,
    found_name VARCHAR(512) NOT NULL,
    found_position INT NOT NULL,
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

CREATE TABLE autokmdb_places (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    place_name VARCHAR(512),
    place_id INT,
    found_name VARCHAR(512) NOT NULL,
    found_position INT NOT NULL,
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

CREATE TABLE autokmdb_others (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT NOT NULL,
    other_id INT NOT NULL,
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

CREATE INDEX idx_news_filtering ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason, newspaper_id);
CREATE INDEX idx_news_sorting ON autokmdb_news (source, mod_time);

CREATE INDEX idx_persons_news_id ON autokmdb_persons (autokmdb_news_id);
CREATE INDEX idx_institutions_news_id ON autokmdb_institutions (autokmdb_news_id);
CREATE INDEX idx_places_news_id ON autokmdb_places (autokmdb_news_id);
CREATE INDEX idx_others_news_id ON autokmdb_others (autokmdb_news_id);

ALTER TABLE autokmdb_news ADD negative_reason INT, ADD is_paywalled INT;
ALTER TABLE autokmdb_news ADD category INT, ADD article_date TIMESTAMP;

CREATE FULLTEXT INDEX idx_news_fulltext_search ON autokmdb_news (title, description, source_url);

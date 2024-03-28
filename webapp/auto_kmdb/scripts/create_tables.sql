CREATE TABLE autokmdb_news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    news_id INT,
    source INT NOT NULL,
    source_url VARCHAR(255) NOT NULL,
    clean_url VARCHAR(255) NOT NULL,
    newspaper_name VARCHAR(255) NOT NULL,
    newspaper_id INT NOT NULL,
    text MEDIUMTEXT,
    title VARCHAR(255),
    description VARCHAR(255),
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    skip_reason INT,
    processing_step INT NOT NULL,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT
);

CREATE TABLE autokmdb_persons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    person_name VARCHAR(255),
    person_id INT,
    found_name VARCHAR(255) NOT NULL,
    found_position INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
);

CREATE TABLE autokmdb_institutions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    institution_name VARCHAR(255),
    institution_id INT,
    found_name VARCHAR(255) NOT NULL,
    found_position INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
);

CREATE TABLE autokmdb_places (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT,
    place_name VARCHAR(255),
    place_id INT,
    found_name VARCHAR(255) NOT NULL,
    found_position INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
);

CREATE TABLE autokmdb_others (
    id INT AUTO_INCREMENT PRIMARY KEY,
    autokmdb_news_id INT NOT NULL,
    other_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    classification_score DOUBLE,
    classification_label INT,
    annotation_label INT,
    cre_time TIMESTAMP DEFAULT '0000-00-00 00:00:00',
    mod_time TIMESTAMP DEFAULT now() ON UPDATE now(),
    mod_id INT,
    version_number INT NOT NULL
);

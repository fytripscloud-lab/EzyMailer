CREATE DATABASE IF NOT EXISTS ezymailer
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ezymailer;

CREATE TABLE IF NOT EXISTS user_db (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NULL,
    password_salt VARCHAR(64) NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO user_db (username, password, role)
SELECT 'admin', 'admin', 'admin'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1
    FROM user_db
    WHERE username = 'admin'
);

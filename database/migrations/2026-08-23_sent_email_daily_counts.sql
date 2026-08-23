-- Replace recipient-level send history with privacy-preserving daily totals.
USE ezymailer;

CREATE TABLE IF NOT EXISTS sent_email_daily (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NULL,
    username VARCHAR(64) NOT NULL,
    sent_date DATE NOT NULL,
    sent_count INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sent_email_daily (user_id, username, sent_date),
    KEY idx_sent_email_daily_user (user_id, sent_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO sent_email_daily (user_id, username, sent_date, sent_count)
SELECT user_id, username, DATE(created_at), COUNT(*)
FROM sent_email_log
GROUP BY user_id, username, DATE(created_at)
ON DUPLICATE KEY UPDATE sent_count = sent_count + VALUES(sent_count);

DROP TABLE IF EXISTS sent_email_log;

CREATE SCHEMA emotions DEFAULT CHARACTER SET utf8mb4;
USE emotions;

CREATE TABLE IF NOT EXISTS emotions.login_user (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(45) NOT NULL,
    password VARCHAR(255) NOT NULL, 
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE INDEX idlogin_user_UNIQUE (id ASC),
    UNIQUE INDEX username_UNIQUE (username ASC)
);

CREATE TABLE IF NOT EXISTS emotions.image_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    input_image VARCHAR(255) NOT NULL,
    output_image VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
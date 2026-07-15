CREATE TABLE IF NOT EXISTS `user` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(32) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    role ENUM('值长','检修班长','厂长','管理员') NOT NULL,
    plant_id INT DEFAULT NULL,
    real_name VARCHAR(32) DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plant_id INT NOT NULL,
    device_name VARCHAR(64) NOT NULL,
    device_type ENUM('过热器','省煤器','蒸发器','引风机','给水泵','炉排液压站') NOT NULL,
    material VARCHAR(32) DEFAULT '',
    original_wall_thickness DECIMAL(5,2) DEFAULT 0,
    min_allowable_thickness DECIMAL(5,2) DEFAULT 0,
    install_date DATE DEFAULT NULL,
    dcs_tag VARCHAR(32) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS alert_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    alert_level ENUM('yellow','orange','red') NOT NULL,
    alert_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    predicted_loss DECIMAL(10,2) DEFAULT 0,
    status ENUM('pending','confirmed','processing','resolved') DEFAULT 'pending',
    confirm_by VARCHAR(32) DEFAULT '',
    confirm_time DATETIME DEFAULT NULL,
    resolution TEXT,
    close_time DATETIME DEFAULT NULL,
    INDEX idx_device_time (device_id, alert_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS work_order (
    id INT PRIMARY KEY AUTO_INCREMENT,
    alert_id INT DEFAULT NULL,
    device_id INT NOT NULL,
    fault_desc TEXT,
    root_cause TEXT,
    action_plan TEXT,
    spare_parts TEXT,
    similar_cases TEXT,
    assignee VARCHAR(32) DEFAULT '',
    status ENUM('draft','issued','in_progress','completed') DEFAULT 'draft',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    complete_time DATETIME DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS kg_relation (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_type VARCHAR(32) NOT NULL,
    fault_mode VARCHAR(128) NOT NULL,
    phenomenon TEXT,
    root_cause TEXT,
    action_plan TEXT,
    spare_parts TEXT,
    source ENUM('manual','NLP_auto') DEFAULT 'manual',
    occurrence_count INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT DEFAULT NULL,
    username VARCHAR(32) DEFAULT '',
    action VARCHAR(64) NOT NULL,
    resource VARCHAR(128) DEFAULT '',
    source_ip VARCHAR(45) DEFAULT '',
    result ENUM('success','failure') NOT NULL,
    detail JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 默认管理员账号: admin / admin123 (bcrypt hash)
INSERT INTO `user` (username, password_hash, role, real_name) VALUES
('admin', '$2b$12$piAFiaXX0yfcYQvGQTUMeOl8xYacE1klljCyBcYgLNJHvktCdBVIC', '管理员', '系统管理员');

-- 创建交易员表
CREATE TABLE traders (
    id SERIAL PRIMARY KEY,
    trader_name VARCHAR(100) NOT NULL,
    professional_title VARCHAR(100) NOT NULL,
    profile_image_url TEXT NOT NULL,
    total_profit DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    followers_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入示例数据
INSERT INTO traders (
    trader_name, 
    professional_title, 
    profile_image_url, 
    total_profit, 
    total_trades, 
    win_rate, 
    followers_count, 
    likes_count
) VALUES 
    (
        'Tom Preston',
        'Senior Forex Trader',
        'https://example.com/avatars/tom.jpg',
        181172.00,
        1250,
        92.5,
        4521,
        25678
    ),
    (
        'Michael Chen',
        'Crypto Expert',
        'https://example.com/avatars/michael.jpg',
        198756.75,
        986,
        88.3,
        3876,
        12543
    ),
    (
        'Sarah Johnson',
        'Stock Market Analyst',
        'https://example.com/avatars/sarah.jpg',
        175890.25,
        875,
        85.7,
        3254,
        10987
    ),
    (
        'David Brown',
        'Technical Analyst',
        'https://example.com/avatars/david.jpg',
        145670.80,
        756,
        83.2,
        2987,
        9876
    ),
    (
        'Emma Davis',
        'Value Hunter',
        'https://example.com/avatars/emma.jpg',
        132450.60,
        645,
        81.5,
        2654,
        8765
    ),
    (
        'James Wilson',
        'Swing Trader',
        'https://example.com/avatars/james.jpg',
        128760.40,
        589,
        79.8,
        2432,
        7654
    ),
    (
        'Lisa Zhang',
        'Day Trader',
        'https://example.com/avatars/lisa.jpg',
        115890.30,
        534,
        78.4,
        2198,
        6543
    ),
    (
        'Robert Taylor',
        'Options Specialist',
        'https://example.com/avatars/robert.jpg',
        98760.25,
        478,
        76.9,
        1987,
        5432
    ),
    (
        'Anna Martinez',
        'Market Strategist',
        'https://example.com/avatars/anna.jpg',
        87650.15,
        423,
        75.3,
        1765,
        4321
    ),
    (
        'Thomas Anderson',
        'Portfolio Manager',
        'https://example.com/avatars/thomas.jpg',
        76540.90,
        367,
        73.8,
        1543,
        3210
    );

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_traders_updated_at
    BEFORE UPDATE ON traders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    role TEXT DEFAULT 'user',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建会员等级表
CREATE TABLE IF NOT EXISTS membership_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    level INTEGER NOT NULL,
    min_trading_volume REAL NOT NULL,
    benefits TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建用户会员关系表
CREATE TABLE IF NOT EXISTS user_membership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    level_id INTEGER NOT NULL,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (level_id) REFERENCES membership_levels (id)
);

-- 创建交易策略表
CREATE TABLE IF NOT EXISTS trading_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_analysis TEXT NOT NULL,
    trading_focus TEXT NOT NULL,
    risk_warning TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 创建策略历史记录表
CREATE TABLE IF NOT EXISTS strategy_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    market_analysis TEXT NOT NULL,
    trading_focus TEXT NOT NULL,
    risk_warning TEXT NOT NULL,
    modified_by INTEGER NOT NULL,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES trading_strategies (id),
    FOREIGN KEY (modified_by) REFERENCES users (id)
);

-- 创建策略权限表
CREATE TABLE IF NOT EXISTS strategy_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    can_create BOOLEAN DEFAULT FALSE,
    can_update BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 为管理员用户添加默认权限
INSERT INTO strategy_permissions (user_id, can_create, can_update, can_delete)
SELECT id, TRUE, TRUE, TRUE
FROM users
WHERE role = 'admin';

-- 创建策略权限触发器
CREATE TRIGGER IF NOT EXISTS check_strategy_permissions
BEFORE INSERT OR UPDATE OR DELETE ON trading_strategies
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM strategy_permissions
            WHERE user_id = NEW.created_by
            AND (
                (TG_OP = 'INSERT' AND can_create = TRUE) OR
                (TG_OP = 'UPDATE' AND can_update = TRUE) OR
                (TG_OP = 'DELETE' AND can_delete = TRUE)
            )
        )
        THEN RAISE(ABORT, 'Permission denied')
    END;
END;

-- 创建VIP策略公告表
CREATE TABLE IF NOT EXISTS vip_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    priority INTEGER DEFAULT 0,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 创建VIP交易表
CREATE TABLE IF NOT EXISTS vip_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_price DECIMAL(15,2) NOT NULL,
    exit_price DECIMAL(15,2),
    quantity DECIMAL(15,2) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    trade_type TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    current_price DECIMAL(15,2),
    pnl DECIMAL(15,2),
    roi DECIMAL(5,2),
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- 创建VIP策略公告更新时间触发器
CREATE TRIGGER update_vip_announcements_updated_at
    BEFORE UPDATE ON vip_announcements
    FOR EACH ROW
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END;

-- 创建VIP交易更新时间触发器
CREATE TRIGGER update_vip_trades_updated_at
    BEFORE UPDATE ON vip_trades
    FOR EACH ROW
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END; 
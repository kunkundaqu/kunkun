-- 查看trader_profiles表的结构
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'trader_profiles'
ORDER BY ordinal_position;

-- 查看trader_profiles表的所有数据
SELECT * FROM trader_profiles;

-- 查看trader_profiles表的记录数量
SELECT COUNT(*) as total_records FROM trader_profiles;

-- 查看trader_profiles表的前5条记录
SELECT * FROM trader_profiles LIMIT 5; 
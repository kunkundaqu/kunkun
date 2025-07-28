-- Trader Profiles Table
-- 交易员档案表

CREATE TABLE public.trader_profiles (
    id                  integer PRIMARY KEY,
    profile_image_url   varchar,
    trader_name         varchar,
    professional_title  varchar,
    years_of_experience integer,
    total_trades        integer,
    win_rate            numeric,
    created_at          timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at          timestamp DEFAULT CURRENT_TIMESTAMP,
    members_count       integer DEFAULT 0,
    likes_count         integer DEFAULT 0
);

-- 添加索引以提高查询性能
CREATE INDEX idx_trader_profiles_trader_name ON public.trader_profiles(trader_name);
CREATE INDEX idx_trader_profiles_win_rate ON public.trader_profiles(win_rate);
CREATE INDEX idx_trader_profiles_created_at ON public.trader_profiles(created_at);

-- 添加注释
COMMENT ON TABLE public.trader_profiles IS '交易员档案信息表';
COMMENT ON COLUMN public.trader_profiles.id IS '主键ID';
COMMENT ON COLUMN public.trader_profiles.profile_image_url IS '头像图片URL';
COMMENT ON COLUMN public.trader_profiles.trader_name IS '交易员姓名';
COMMENT ON COLUMN public.trader_profiles.professional_title IS '专业头衔';
COMMENT ON COLUMN public.trader_profiles.years_of_experience IS '经验年数';
COMMENT ON COLUMN public.trader_profiles.total_trades IS '总交易次数';
COMMENT ON COLUMN public.trader_profiles.win_rate IS '胜率';
COMMENT ON COLUMN public.trader_profiles.created_at IS '创建时间';
COMMENT ON COLUMN public.trader_profiles.updated_at IS '更新时间';
COMMENT ON COLUMN public.trader_profiles.members_count IS '成员数量';
COMMENT ON COLUMN public.trader_profiles.likes_count IS '点赞数量'; 
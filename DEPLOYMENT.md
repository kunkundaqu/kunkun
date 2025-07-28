# 部署说明

## 环境变量配置

### 必需的环境变量

1. **SUPABASE_URL**
   - 值: `https://rwlziuinlbazgoajkcme.supabase.co`
   - 说明: 您的Supabase项目URL

2. **SUPABASE_KEY**
   - 值: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3bHppdWlubGJhemdvYWprY21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTE4MDA2MiwiZXhwIjoyMDYwNzU2MDYyfQ.HAAXKlwasbIoq27IHRUn4gZoMfzGvUfsI4pt4NqCThk`
   - 说明: 您的Supabase服务角色密钥

3. **FLASK_SECRET_KEY**
   - 值: 任意随机字符串（建议使用强密码生成器生成）
   - 说明: Flask应用的密钥，用于会话加密

4. **PORT**
   - 值: `8000`
   - 说明: 应用运行端口

### 在Render上部署

1. 将代码推送到GitHub
2. 在Render上连接您的GitHub仓库
3. 环境变量已经在 `render.yaml` 中配置好了
4. 点击部署

### 在其他平台部署

如果您在其他平台部署（如Heroku、Railway等），请手动设置以下环境变量：

```bash
SUPABASE_URL=https://rwlziuinlbazgoajkcme.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3bHppdWlubGJhemdvYWprY21lIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTE4MDA2MiwiZXhwIjoyMDYwNzU2MDYyfQ.HAAXKlwasbIoq27IHRUn4gZoMfzGvUfsI4pt4NqCThk
FLASK_SECRET_KEY=your_secret_key_here_change_this_in_production
PORT=8000
```

### 本地开发

1. 创建 `.env` 文件（注意：此文件已被.gitignore忽略）
2. 添加上述环境变量
3. 运行 `python app.py`

## 注意事项

- 请确保 `SUPABASE_KEY` 是服务角色密钥，不是匿名密钥
- 在生产环境中，请更改 `FLASK_SECRET_KEY` 为安全的随机字符串
- 不要将包含真实密钥的 `.env` 文件提交到版本控制系统 
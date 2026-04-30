# AI张老师·数字分身 - 登录认证系统安装指南

## 概述

本系统为AI张老师·数字分身添加了完整的用户登录认证功能，包括：
- 用户注册、登录、退出
- 基于用户ID的聊天历史记录
- 会话管理
- 数据库存储（使用SQLite，可迁移到MySQL）

## 系统架构

```
app_with_auth.py          # 主应用文件（带认证）
models.py                # 数据库模型定义
auth.py                  # 认证和授权功能
templates/login.html     # 登录页面
templates/register.html  # 注册页面
static/css/auth.css      # 认证页面样式
app.db                   # SQLite数据库文件（自动创建）
```

## 安装步骤

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者手动安装
pip install flask flask-sqlalchemy flask-login werkzeug bcrypt python-dotenv requests openai psutil
```

### 2. 启动应用

```bash
# 方法1: 使用启动脚本
python start_app_with_auth.py

# 方法2: 直接运行
python app_with_auth.py
```

### 3. 访问应用

应用启动后，访问以下地址：

- 首页: http://localhost:5002
- 登录页面: http://localhost:5002/login
- 注册页面: http://localhost:5002/register
- 应用版（需要登录）: http://localhost:5002/app
- 教育版（需要登录）: http://localhost:5002/pedu

### 4. 测试账户

系统会自动创建以下测试账户：

- **普通用户**: testuser / test123
- **管理员**: admin / admin123

## 功能说明

### 用户注册

1. 访问注册页面
2. 填写用户名、密码等信息
3. 系统验证用户名唯一性
4. 密码强度检查
5. 注册成功后跳转到登录页面

### 用户登录

1. 访问登录页面
2. 输入用户名和密码
3. 可选择"记住我"选项
4. 登录成功后跳转到应用页面

### 聊天历史记录

- 所有聊天记录都会关联到用户ID
- 按会话ID分组存储
- 支持查看历史聊天记录
- 数据持久化到数据库

### 会话管理

- 每个登录会话有唯一ID
- 会话有效期7天
- 支持会话续期
- 支持主动退出会话

## API接口

### 认证相关

```http
POST /api/login
Content-Type: application/json

{
    "username": "testuser",
    "password": "test123",
    "remember": false
}
```

```http
POST /api/register
Content-Type: application/json

{
    "username": "newuser",
    "password": "password123",
    "email": "user@example.com",
    "full_name": "新用户"
}
```

```http
GET /api/user/info
Authorization: Bearer {token}
```

```http
GET /api/chat/history?session_id={session_id}&limit=50
Authorization: Bearer {token}
```

### 聊天接口（需要登录）

```http
POST /chat
Content-Type: application/json
Authorization: Bearer {token}

{
    "question": "你好，你是谁？",
    "need_audio": true,
    "session_id": "optional_session_id"
}
```

```http
POST /app/chat
Content-Type: application/json
Authorization: Bearer {token}

{
    "question": "基于我的成绩推荐专业",
    "context": "我的成绩是...",
    "use_cache": true,
    "session_id": "optional_session_id"
}
```

## 数据库设计

### users 表（用户表）
- id: 主键
- username: 用户名（唯一）
- password_hash: 密码哈希
- email: 邮箱（唯一）
- full_name: 姓名
- created_at: 创建时间
- updated_at: 更新时间
- last_login: 最后登录时间
- is_active: 是否激活

### user_sessions 表（用户会话表）
- id: 主键
- user_id: 用户ID（外键）
- session_id: 会话ID（唯一）
- ip_address: IP地址
- user_agent: 用户代理
- created_at: 创建时间
- expires_at: 过期时间
- is_active: 是否活跃

### chat_history 表（聊天历史表）
- id: 主键
- user_id: 用户ID（外键）
- session_id: 会话ID
- message_type: 消息类型（user/assistant/system）
- content: 消息内容
- context: 上下文信息
- response_time: 响应时间
- created_at: 创建时间

## 迁移到MySQL

如果需要迁移到MySQL，修改 `models.py` 中的数据库配置：

```python
# 修改 init_db 函数中的数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost:3306/agent_f'
```

然后安装MySQL驱动：
```bash
pip install pymysql
```

## 安全注意事项

1. **生产环境配置**:
   - 修改 `SECRET_KEY`
   - 启用HTTPS
   - 使用强密码策略
   - 定期备份数据库

2. **密码安全**:
   - 使用bcrypt哈希算法
   - 密码最小长度6位
   - 建议启用密码强度检查

3. **会话安全**:
   - 会话有效期7天
   - 支持会话续期
   - 支持主动退出

## 故障排除

### 1. 数据库创建失败
- 检查文件写入权限
- 确保磁盘空间充足
- 检查SQLite版本兼容性

### 2. 登录失败
- 检查用户名和密码
- 查看数据库中的用户记录
- 检查密码哈希算法

### 3. 会话过期太快
- 检查系统时间设置
- 调整会话有效期配置
- 检查浏览器Cookie设置

### 4. 聊天历史不保存
- 检查数据库连接
- 查看用户登录状态
- 检查数据库写入权限

## 扩展功能建议

1. **邮箱验证**: 注册时发送验证邮件
2. **密码重置**: 通过邮箱重置密码
3. **角色权限**: 添加用户角色和权限控制
4. **第三方登录**: 集成微信、GitHub等第三方登录
5. **审计日志**: 记录用户操作日志
6. **数据导出**: 支持聊天历史导出

## 技术支持

如有问题，请检查：
1. 日志文件: `logs/app.log`
2. 数据库文件: `app.db`
3. 系统依赖: `requirements.txt`

或联系开发团队获取支持。
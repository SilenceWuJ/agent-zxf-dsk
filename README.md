# AI张老师数字分身

一个基于AI张老师风格的高考志愿咨询助手，提供幽默、直率、务实的志愿规划建议。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <项目地址>
cd zhangxuefeng-ai

# 创建虚拟环境（可选但推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的API密钥
# 需要配置以下API密钥：
# - DeepSeek API密钥
# - 阿里云百炼API密钥
```

### 3. 运行应用

```bash
# 启动Flask应用
python app_.py

# 或使用gunicorn（生产环境）
# gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. 访问应用

打开浏览器访问：http://localhost:5000

## 🔧 配置说明

### 必需配置

1. **DeepSeek API密钥**
   - 注册地址: https://platform.deepseek.com
   - 获取API密钥: https://platform.deepseek.com/api_keys

2. **阿里云百炼API密钥**
   - 注册地址: https://www.aliyun.com/product/dashscope
   - 获取API密钥: https://dashscope.console.aliyun.com/apiKey

### 可选配置

- **阿里云知识库ID**: 如果使用阿里云知识库功能
- **腾讯云配置**: 如果启用语音合成功能

## 📁 项目结构

```
.
├── app.py                 # Flask主应用
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量模板
├── .env                  # 环境变量（本地配置，不提交）
├── templates/            # HTML模板
│   ├── base.html        # 基础模板
│   └── index.html       # 主页面
├── static/              # 静态资源
│   ├── css/
│   │   └── style.css   # 样式文件
│   └── js/
│       └── main.js     # JavaScript文件
├── main.html            # 原始简单页面
└── README.md           # 说明文档
```

## 🎯 功能特性

### ✅ 已实现功能
- 美观的Web界面，响应式设计
- AI张老师风格对话
- 实时聊天交互
- 移动端适配
- 环境变量配置管理
- 错误处理和用户提示

### 🔄 工作流程
1. 用户输入问题
2. 从阿里云知识库检索相关信息
3. 结合检索结果调用DeepSeek生成回答
4. 返回AI张老师风格的回答

### 🎨 界面特点
- 现代化UI设计
- 渐变背景和卡片设计
- 加载动画和状态提示
- 用户偏好保存
- 侧边栏信息展示

## 🔒 安全注意事项

1. **API密钥安全**
   - 不要将 `.env` 文件提交到版本控制
   - 确保 `.env` 在 `.gitignore` 中
   - 定期轮换API密钥

2. **生产环境部署**
   - 使用环境变量而非文件存储密钥
   - 启用HTTPS
   - 配置适当的防火墙规则
   - 使用进程管理工具（如systemd, supervisor）

## 🐛 故障排除

### 常见问题

1. **应用无法启动**
   ```bash
   # 检查依赖是否安装
   pip install -r requirements.txt
   
   # 检查端口是否被占用
   lsof -i :5000
   ```

2. **API调用失败**
   - 检查 `.env` 文件中的API密钥是否正确
   - 检查网络连接
   - 查看控制台错误信息

3. **样式不加载**
   - 检查浏览器控制台是否有404错误
   - 确保 `static` 目录存在且文件正确

### 日志查看
应用运行时会在控制台输出日志，包含：
- 环境变量检查结果
- API调用状态
- 错误信息

## 📞 支持与贡献

如有问题或建议，请：
1. 查看控制台错误信息
2. 检查环境变量配置
3. 提交Issue或Pull Request

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关API服务的使用条款。

---

**温馨提示**: 本应用提供的建议仅供参考，实际志愿填报请结合个人情况和官方信息。
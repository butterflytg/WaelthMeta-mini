# 财小助 - 微信小程序版

一个基于微信小程序的智能记账助手，支持自然语言记账和查询功能。

## 项目结构

```
WealthMeta-mini/
├── miniprogram/                # 微信小程序前端代码
│   ├── app.js                  # 小程序入口文件
│   ├── app.json                # 小程序全局配置
│   ├── app.wxss                # 小程序全局样式
│   ├── pages/                  # 页面文件夹
│   │   └── index/             # 主页面
│   │       ├── index.js       # 主页面逻辑
│   │       ├── index.json     # 主页面配置
│   │       ├── index.wxml     # 主页面模板
│   │       └── index.wxss     # 主页面样式
│   └── utils/                  # 工具类文件夹
│       └── request.js         # 网络请求工具
├── agent/                      # 后端业务逻辑
│   └── workflow.py            # 工作流处理
├── db/                         # 数据库相关
│   └── SQLiteDB.py            # SQLite数据库操作
├── log/                        # 日志相关
│   └── logger.py              # 日志处理
├── prompts/                    # 提示词模板
├── utils/                      # 后端工具类
│   └── LLMUtil.py             # LLM工具类
├── app.py                      # 后端服务器入口
├── requirements.txt            # Python依赖
└── project.config.json         # 微信小程序项目配置
```

## 功能特点

1. 自然语言记账
   - 支持多种记账表达方式
   - 智能识别金额和类别
   - 自动记录时间

2. 智能查询
   - 支持多维度查询
   - 自然语言交互
   - 数据可视化展示

3. 个性化对话
   - 支持三种对话风格：轻松、幽默、正式
   - 智能上下文理解
   - 人性化回复

## 技术栈

- 前端：微信小程序
- 后端：Python Flask + Gradio
- 数据库：SQLite
- AI：LangChain + LLM

## 安装和运行

### 后端服务

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行服务器：
```bash
python app.py
```

服务器将在以下地址运行：
- Flask API: http://localhost:7860
- Gradio界面: http://localhost:7861

### 微信小程序

1. 使用微信开发者工具打开项目
2. 在 project.config.json 中配置你的小程序 appid
3. 在 app.js 中修改 baseUrl 为你的服务器地址
4. 点击"编译"预览小程序

## 开发说明

### 后端开发

- 主要业务逻辑在 `agent/workflow.py` 中
- API接口在 `app.py` 中定义
- 数据库操作在 `db/SQLiteDB.py` 中

### 前端开发

- 页面布局在 `pages/index/index.wxml` 中
- 样式定义在 `pages/index/index.wxss` 中
- 业务逻辑在 `pages/index/index.js` 中
- 网络请求封装在 `utils/request.js` 中

## 注意事项

1. 开发环境配置
   - 确保 Python 环境正确配置
   - 安装所有必要的依赖包
   - 配置正确的数据库连接

2. 微信小程序配置
   - 在开发者工具中开启"不校验合法域名"
   - 确保服务器地址配置正确
   - 注意小程序的发布配置

3. 调试说明
   - 后端日志在 log 目录下
   - 前端调试使用微信开发者工具
   - API测试可以使用 Postman 等工具

## 维护说明

1. 代码规范
   - 遵循 PEP 8 Python 代码规范
   - 使用 ESLint 进行前端代码检查
   - 保持代码注释完整

2. 版本控制
   - 使用 Git 进行版本管理
   - 遵循语义化版本规范
   - 保持提交信息清晰

3. 部署流程
   - 测试环境部署
   - 生产环境部署
   - 回滚机制

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
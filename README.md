# WealthMate - 个人财务助手

## 项目概述
WealthMate是一个基于Python开发的个人财务管理助手，它能够帮助用户记录和管理日常收支，提供智能对话式的记账体验。

## 主要功能
- 智能对话式记账：支持自然语言输入记账信息
- 多用户管理：支持多个用户独立使用
- 收支分类：自动对收支进行分类管理
- 数据统计：提供收支情况的统计和分析
- 自定义语气：支持轻松、幽默、正式三种回复风格

## 技术架构
- 前端界面：使用Gradio构建简洁的Web界面
- 数据存储：使用SQLite数据库
- 智能对话：集成语言模型实现智能交互
- 日志系统：使用loguru实现分级日志管理

## 项目结构
```
├── agent/              # 智能代理模块
│   ├── workflow.py     # 工作流程处理
│   └── LlmChainGenerate.py  # 语言模型链生成
├── db/                 # 数据库模块
│   └── SQLiteDB.py    # SQLite数据库操作
├── log/               # 日志模块
│   ├── logger.py      # 日志处理
│   └── log_config.json # 日志配置
├── utils/             # 工具模块
│   ├── GraphUtil.py   # 图形处理工具
│   └── PrintUtils.py  # 打印工具
├── prompts/           # 提示词模板
├── app.py            # Web应用入口
└── main.py           # 命令行入口
```

## 安装说明
1. 克隆项目代码
```bash
git clone https://github.com/butterflytg/WealthMeta1.git
cd WealthMate
```

2. 安装依赖包
```bash
pip install -r requirements.txt
```

## 使用方法
### Web界面启动
```bash
python app.py
```
启动后访问本地Web界面，支持以下功能：
- 选择语气风格（轻松/幽默/正式）
- 输入自然语言进行记账
- 查询历史记录和统计信息

### 命令行启动
```bash
python main.py
```
在命令行中直接输入记账信息或查询指令。

## 示例用法
1. 记录支出："我今天买奶茶花了20元"
2. 记录收入："我昨天收到工资5000元
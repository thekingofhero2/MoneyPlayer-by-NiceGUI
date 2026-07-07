# MoneyPrinter by NiceGUI

基于 FastAPI + NiceGUI 的全自动视频生成应用。

## 项目简介

本项目分为两个主要部分：

1. **FastAPI + NiceGUI 全栈模板**：提供用户认证、数据库集成等基础功能
2. **app_videomaker 视频制作模块**：核心视频生成功能

## app_videomaker 模块来源说明

**重要提示**：`src/app_videomaker/` 目录下的视频制作功能大部分代码来自 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 项目。

本项目在 MoneyPrinterTurbo 基础上进行了以下扩展：

- 集成 NiceGUI 前端界面
- 添加 Web API 接口
- 支持用户认证和任务管理
  如需了解视频制作的核心算法和逻辑，请参考 MoneyPrinterTurbo 项目。

## 功能特性

### 视频制作 (app_videomaker)

- **AI 脚本生成**：使用大语言模型自动生成视频脚本
- **多源素材支持**：支持 Pexels、Pixabay 在线素材以及本地素材
- **语音合成**：支持 Azure TTS 多种语音
- **字幕生成**：自动生成并渲染视频字幕
- **视频剪辑**：支持多种视频拼接模式
- **背景音乐**：内置多种 BGM 类型
- **任务管理**：支持多任务并行处理

### Web 应用

- **用户认证**：JWT 令牌认证
- **视频脚本管理**：创建、编辑、查看视频脚本
- **任务管理**：查看和管理视频生成任务
- **配置管理**：灵活的视频参数配置

## 技术栈

- **后端**：FastAPI
- **前端**：NiceGUI
- **数据库**：PostgreSQL + Redis
- **视频处理**：MoviePy
- **AI 服务**：支持多种 LLM API

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 数据库
- Redis（可选，用于分布式部署）

### 安装部署

1. 克隆项目

```bash
git clone https://github.com/harry0703/MoneyPrinter-by-NiceGUI.git
cd MoneyPrinter-by-NiceGUI
```

2. 配置环境变量

```bash
cp .env.template .env
# 编辑 .env 文件，填入必要的 API 密钥
```

3. 启动数据库

```bash
docker-compose up -d db
```

4. 安装依赖

```bash
pip install -r requirements.txt
```

5. 运行应用

```bash
python app.py
```

访问 http://localhost:8080 查看应用界面。

## 项目结构

```
src/
├── app_videomaker/          # 视频制作核心模块（来自 MoneyPrinterTurbo）
│   ├── config/              # 配置管理
│   ├── controllers/         # 控制器
│   ├── models/              # 数据模型
│   ├── services/            # 业务服务
│   │   ├── llm.py           # LLM 服务
│   │   ├── material.py      # 素材获取
│   │   ├── video.py         # 视频处理
│   │   ├── voice.py         # 语音合成
│   │   ├── subtitle.py      # 字幕处理
│   │   ├── task.py          # 任务调度
│   │   └── upload_post.py   # 上传发布
│   └── utils/               # 工具函数
├── frontend/                # NiceGUI 前端页面
│   ├── pages/               # 页面组件
│   ├── components/          # 通用组件
│   └── layouts/             # 布局组件
├── backend/                 # FastAPI 后端接口
├── db/                      # 数据库初始化
└── repositories/            # 数据访问层
```

## 配置说明

视频制作的主要配置项：

| 配置项               | 说明                                |
| -------------------- | ----------------------------------- |
| `video_source`     | 视频素材来源 (pexels/pixabay/local) |
| `video_aspect`     | 视频比例 (portrait/landscape)       |
| `voice_name`       | 语音名称                            |
| `subtitle_enabled` | 是否启用字幕                        |
| `bgm_type`         | 背景音乐类型                        |

详细配置请参考 `config.toml` 模板。

## License

基于 MoneyPrinterTurbo 项目许可。

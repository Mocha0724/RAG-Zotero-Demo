# Zotero RAG Demo 项目结构

本文档详细描述了Zotero RAG Demo项目的结构、文件组织和主要组件功能，方便开发者和AI助手快速理解和维护这个项目。

## 目录结构

```
RAG_Demo/
├── app/                    # 应用程序主要代码
│   ├── api/                # 后端API
│   │   ├── llm.py          # 大语言模型接口
│   │   ├── main.py         # FastAPI主入口
│   │   ├── models.py       # 数据模型定义
│   │   ├── rag.py          # RAG检索引擎
│   │   └── routes.py       # API路由定义
│   ├── components/         # 前端组件
│   └── pages/              # 前端页面
│       └── index.html      # 主页面
├── data/                   # 数据文件
│   ├── raw/                # 原始Zotero导出数据
│   ├── processed/          # 处理后的文献数据
│   └── embeddings/         # 向量嵌入和数据库
├── models_cache/           # 模型缓存目录
├── scripts/                # 处理脚本
│   ├── create_embeddings.py # 生成向量嵌入
│   └── extract_zotero.py   # 从Zotero提取数据
├── .env                    # 环境变量配置
├── .env.example            # 环境变量示例
├── environment.yml         # Conda环境配置
├── README.md               # 项目说明
├── requirements.txt        # Python依赖包
├── server.py               # 服务器启动脚本
└── structure.md            # 本文档(项目结构说明)
```

## 核心组件

### 1. 数据处理流程

#### a. 数据提取 (`scripts/extract_zotero.py`)

- **功能**: 从Zotero导出文件中提取文献数据
- **输入**: Zotero导出的文件(BibTeX, CSV等)
- **输出**: `data/processed/processed_documents.json`
- **关键函数**:
  - `extract_zotero_data()`: 提取Zotero数据并转换为统一格式
  - `process_pdf_files()`: 处理PDF文件并提取全文(如果有)

#### b. 向量嵌入生成 (`scripts/create_embeddings.py`)

- **功能**: 将处理后的文献分块并生成向量嵌入
- **输入**: `data/processed/processed_documents.json`
- **输出**: `data/embeddings/` 向量数据库文件
- **关键类与方法**:
  - `DocumentProcessor`: 主处理类
    - `process_documents()`: 将文档分块
    - `create_embeddings()`: 生成嵌入向量
  - `SimpleBOWEmbeddings`: 备选词袋模型嵌入

### 2. 后端API (`app/api/`)

#### a. API入口 (`main.py`)

- **功能**: FastAPI应用主入口
- **关键组件**:
  - FastAPI应用实例化
  - CORS中间件配置
  - 静态文件服务配置
  - 路由注册

#### b. RAG检索引擎 (`rag.py`)

- **功能**: 从向量数据库检索相关文档
- **关键类与方法**:
  - `RAGEngine`: 核心检索引擎
    - `retrieve()`: 检索与查询相关的文档
    - `get_knowledge_base_status()`: 获取知识库状态

#### c. 大语言模型接口 (`llm.py`)

- **功能**: 与DeepSeek API交互
- **关键类与方法**:
  - `DeepSeekLLM`: API交互类
    - `generate_answer()`: 生成回答

#### d. 数据模型 (`models.py`)

- **功能**: 定义API的数据模型
- **主要模型**:
  - `ChatRequest`: 聊天请求模型
  - `ChatResponse`: 聊天响应模型
  - `Source`: 引用源模型

#### e. API路由 (`routes.py`)

- **功能**: 定义API路由
- **主要路由**:
  - `/api/chat`: 处理聊天请求
  - `/api/status`: 获取知识库状态

### 3. 前端 (`app/pages/index.html`)

- **功能**: 提供用户界面
- **主要功能**:
  - 聊天界面
  - 设置面板
  - 引用源展示
  - 状态信息显示

### 4. 服务器启动 (`server.py`)

- **功能**: 启动FastAPI服务器
- **关键组件**:
  - 命令行参数解析
  - uvicorn服务器配置

## 关键流程

### 1. 数据处理流程

```
Zotero导出文件 → extract_zotero.py → 处理后的文档 → create_embeddings.py → 向量数据库
```

### 2. 查询处理流程

```
用户查询 → FastAPI路由 → RAG检索引擎 → 检索相关文档 → DeepSeek LLM生成回答 → 返回结果给用户
```

## 配置项

### 1. 环境变量 (`.env`)

- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `DEEPSEEK_MODEL`: 使用的DeepSeek模型名称
- `EMBEDDING_MODEL`: 使用的嵌入模型
- `VECTOR_DB_PATH`: 向量数据库路径
- `APP_HOST`和`APP_PORT`: 应用服务器配置

### 2. 可调参数

- 相似度阈值(`similarity_threshold`): 默认为0.2
- 最大引用源数量(`max_sources`): 默认为5
- 文本分块大小(`chunk_size`): 默认为1000
- 分块重叠大小(`chunk_overlap`): 默认为200
- 批处理大小(`batch_size`): 默认为50

## 依赖关系

### 核心依赖

- `sentence-transformers`: 用于生成文本嵌入
- `langchain`和`langchain-community`: 用于文档处理和向量检索
- `fastapi`: 提供API服务
- `chromadb`: 向量数据库
- `python-dotenv`: 环境变量管理
- `requests`: API调用

### 版本兼容性

- `huggingface_hub==0.16.4`: 与`sentence-transformers`兼容
- `sentence-transformers==2.2.2`: 避免`init_empty_weights`错误

## 扩展和修改指南

### 添加新的嵌入模型

1. 在`.env`文件中修改`EMBEDDING_MODEL`
2. 注意确保新模型维度与已有嵌入匹配，或重新生成嵌入

### 修改检索参数

1. 在`app/api/rag.py`中修改`retrieve`方法的参数
2. 或在前端设置面板中调整参数

### 整合新的LLM

1. 创建新的LLM接口类，类似于`DeepSeekLLM`
2. 在`app/api/routes.py`中注册和使用新的LLM

## 常见问题解决

### 嵌入维度不匹配

问题表现为错误:`Embedding dimension X does not match collection dimensionality Y`
解决方案:
1. 确保`.env`中的`EMBEDDING_MODEL`与创建嵌入时使用的模型匹配
2. 或者清空`data/embeddings`目录并重新运行`create_embeddings.py`

### 导入错误

问题表现为各种模块导入错误
解决方案:
1. 确保已激活`rag_demo`环境
2. 安装指定版本的依赖:`pip install --force-reinstall huggingface_hub==0.16.4 sentence-transformers==2.2.2`

### 检索质量问题

问题表现为检索结果与问题不相关
解决方案:
1. 使用英文提问，因为大多数学术文献为英文
2. 降低相似度阈值
3. 确保知识库包含相关文献 
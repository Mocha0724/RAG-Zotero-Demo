# Zotero RAG Demo

基于Zotero文献库的检索增强生成(RAG)演示系统，可将学术文献知识库与大语言模型结合，提供智能问答功能。

## 功能特点

- 简洁的对话界面，支持基于文献的智能问答
- 支持导入Zotero文献库作为知识库
- 使用DeepSeek API作为大语言模型
- 显示引用源，支持溯源到原始文献
- 可调整相关性阈值和最大引用数量
- 优化的分批向量嵌入处理，适合大型文献库
- 本地缓存模型，避免重复下载

## 系统架构

本项目采用以下技术栈：

- **前端**: HTML/CSS/JavaScript，使用Tailwind CSS
- **后端**: FastAPI (Python)
- **向量数据库**: Chroma
- **文本处理**: LangChain
- **嵌入模型**: Sentence Transformers
- **大语言模型**: DeepSeek API
- **环境管理**: Conda

## 快速开始

### 环境准备

1. 确保已安装Conda（推荐使用Miniconda）
2. 注册并获取DeepSeek API密钥
3. 准备导出的Zotero文献库数据

### 安装步骤

1. 克隆仓库（或直接下载代码）

```bash
git clone https://github.com/yourusername/RAG_Demo.git
cd RAG_Demo
```

2. 创建并激活Conda环境

```bash
conda env create -f environment.yml
conda activate rag_demo
```

3. 安装依赖包

```bash
pip install -r requirements.txt
pip install python-dotenv sentence-transformers==2.2.2 huggingface_hub==0.16.4
```

4. 配置环境变量

复制`.env.example`文件为`.env`，并填入您的API密钥：

```bash
cp .env.example .env
# 编辑.env文件，填入DeepSeek API密钥
```

### 数据处理

1. 将Zotero导出的数据（BibTeX、CSV等）放入`data/raw`目录
2. 运行数据处理脚本：

```bash
python scripts/extract_zotero.py
python scripts/create_embeddings.py
```

数据处理说明：
- `create_embeddings.py` 会显示详细的进度条和预计完成时间
- 大型文献库处理可能需要较长时间，请耐心等待
- 嵌入模型会自动缓存在 `models_cache` 目录

### 启动服务器

```bash
python server.py
```

然后在浏览器中访问：

- 网页界面：http://localhost:8000/app/pages/index.html
- API文档：http://localhost:8000/docs

## 详细使用说明

### 导入Zotero数据

本系统支持多种方式导入Zotero数据：

1. **导出文件**：
   - 在Zotero中选择要导出的文献集合
   - 右键 -> 导出集合
   - 选择格式（BibTeX, CSV等）
   - 将导出文件保存到`data/raw`目录

2. **通过API**（可选）：
   - 获取Zotero API密钥
   - 在`.env`文件中配置Zotero API相关变量
   - 运行：`python scripts/extract_zotero.py --api`

### 创建知识库

```bash
# 分析文献并提取信息
python scripts/extract_zotero.py

# 生成向量嵌入
python scripts/create_embeddings.py --chunk-size 1000 --chunk-overlap 200
```

参数说明：
- `--chunk-size`：文本分块大小（默认1000）
- `--chunk-overlap`：分块重叠大小（默认200）

### 使用聊天界面

1. 在浏览器中访问 http://localhost:8000/app/pages/index.html
2. **推荐使用英文提问**，这样能获得更好的检索结果
3. 输入与您文献库相关的问题
4. 系统会检索相关文献并生成回答
5. 点击"显示引用源"可查看回答的引用来源

> **注意**：使用英文提问通常能获得更好的检索效果，因为学术文献多为英文，嵌入模型对英文-英文匹配的效果优于中文-英文匹配。

### 调整设置

在聊天界面中点击"设置"按钮，可以调整：
- 最大引用源数量
- 相似度阈值（影响检索结果的相关性过滤）

## 高级配置

### 修改嵌入模型

在`.env`文件中，您可以修改使用的嵌入模型：

```
# 默认使用768维的模型
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# 也可以使用更轻量的384维模型（需要重新生成嵌入）
# EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

注意：更改嵌入模型后需要重新运行`create_embeddings.py`生成新的向量数据库。

### 批处理设置

对于大型文献库，可以调整`create_embeddings.py`中的批处理大小：

```python
# 默认批处理大小为50
batch_size = 50  # 更小的批次大小，减少内存使用
```

较小的批处理大小会使用更少的内存，但处理时间可能更长。

## 常见问题

### 无法连接DeepSeek API

- 检查API密钥是否正确
- 确认网络连接正常
- 检查是否超出API使用限制

### 知识库为空

- 确保已运行数据处理脚本
- 检查Zotero导出文件是否正确放置在`data/raw`目录
- 检查处理日志是否有错误信息

### 检索效果不理想

- 尝试使用英文提问，因为多数学术文献是英文的
- 降低相似度阈值（默认为0.2）
- 使用更具体、更专业的术语
- 确认知识库中包含与问题相关的文献

### 依赖包问题

如果遇到依赖包版本冲突问题，尝试以下命令：

```bash
pip install --force-reinstall huggingface_hub==0.16.4 sentence-transformers==2.2.2
pip install python-dotenv
```

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交Pull Request或Issues来改进这个项目。 
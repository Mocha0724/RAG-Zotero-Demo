#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG检索引擎
负责从向量数据库中检索相关文档并提供上下文
"""

import os
import time
import sys
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置HuggingFace缓存目录
os.environ['TRANSFORMERS_CACHE'] = os.path.join(os.getcwd(), 'models_cache')
os.environ['HF_HOME'] = os.path.join(os.getcwd(), 'models_cache')
os.environ['HF_DATASETS_CACHE'] = os.path.join(os.getcwd(), 'models_cache')
print(f"设置模型缓存目录: {os.path.join(os.getcwd(), 'models_cache')}")

# 定义一个简单的词袋模型作为备选嵌入方法
class SimpleBOWEmbeddings:
    """简单的词袋模型嵌入，作为备选方案"""
    
    def __init__(self, dim=768):
        """初始化简单嵌入模型"""
        self.dim = dim
        self.word_vectors = {}
        self.rng = np.random.RandomState(42)
        print("初始化简单词袋模型嵌入")
    
    def _get_word_vector(self, word):
        """获取词向量，如果不存在则创建"""
        if word not in self.word_vectors:
            self.word_vectors[word] = self.rng.randn(self.dim)
        return self.word_vectors[word]
    
    def embed_documents(self, texts):
        """嵌入文档列表"""
        results = []
        for text in texts:
            results.append(self.embed_query(text))
        return results
    
    def embed_query(self, text):
        """嵌入单个查询"""
        words = text.lower().split()
        if not words:
            return np.zeros(self.dim)
        
        # 计算所有词向量的平均值
        vectors = [self._get_word_vector(word) for word in words]
        embedding = np.mean(vectors, axis=0)
        
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()

# 加载向量数据
class SimpleVectorStore:
    """简单向量存储类"""
    
    def __init__(self, persist_directory, embedding_function=None):
        """初始化简单向量存储"""
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self._collection = SimpleCollection(persist_directory)
        print(f"初始化简单向量存储: {persist_directory}")
        
    def similarity_search_with_relevance_scores(self, query, k=5):
        """相似度搜索"""
        # 将查询转换为向量
        query_embedding = self.embedding_function.embed_query(query)
        
        # 加载所有文档向量
        index_path = Path(self.persist_directory) / "simple_index.json"
        
        if not index_path.exists():
            # 尝试找到embeddings.json
            embeddings_path = Path(self.persist_directory) / "embeddings.json"
            if embeddings_path.exists():
                print(f"使用embeddings.json: {embeddings_path}")
                return self._search_from_embeddings(embeddings_path, query_embedding, k)
            
            print(f"索引文件不存在: {index_path}")
            return []
        
        # 加载索引
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # 计算相似度
        results = []
        for vector_item in index["vectors"]:
            doc_embedding = vector_item["embedding"]
            doc_id = vector_item["id"]
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            results.append((doc_id, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前k个结果
        top_results = results[:k]
        
        # 加载文档内容
        docs_with_scores = []
        for doc_id, score in top_results:
            doc = self._load_document(doc_id)
            if doc:
                docs_with_scores.append((doc, score))
        
        return docs_with_scores
    
    def _search_from_embeddings(self, embeddings_path, query_embedding, k):
        """从embeddings.json中搜索"""
        # 加载所有嵌入
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            all_embeddings = json.load(f)
        
        # 计算相似度
        results = []
        for item in all_embeddings:
            doc_embedding = item["embedding"]
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            
            # 创建Document对象
            doc = SimpleDocument(
                page_content=item["text"],
                metadata=item["metadata"]
            )
            
            results.append((doc, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前k个结果
        return results[:k]
    
    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        dot_product = sum(a*b for a, b in zip(vec1, vec2))
        norm1 = sum(a*a for a in vec1) ** 0.5
        norm2 = sum(b*b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    def _load_document(self, doc_id):
        """加载文档内容"""
        # 从embeddings.json加载文档
        embeddings_path = Path(self.persist_directory) / "embeddings.json"
        if not embeddings_path.exists():
            return None
        
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            all_embeddings = json.load(f)
        
        # 查找匹配的文档
        for item in all_embeddings:
            if item["id"] == doc_id:
                return SimpleDocument(
                    page_content=item["text"],
                    metadata=item["metadata"]
                )
        
        return None

class SimpleCollection:
    """简单集合类"""
    
    def __init__(self, persist_directory):
        """初始化简单集合"""
        self.persist_directory = persist_directory
    
    def count(self):
        """计算文档数量"""
        embeddings_path = Path(self.persist_directory) / "embeddings.json"
        if not embeddings_path.exists():
            return 0
        
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return len(data)
    
    def get(self):
        """获取所有文档"""
        embeddings_path = Path(self.persist_directory) / "embeddings.json"
        if not embeddings_path.exists():
            return {"ids": [], "metadatas": []}
        
        with open(embeddings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        ids = [item["id"] for item in data]
        metadatas = [item["metadata"] for item in data]
        
        return {
            "ids": ids,
            "metadatas": metadatas
        }

class SimpleDocument:
    """简单文档类"""
    
    def __init__(self, page_content, metadata=None):
        """初始化简单文档"""
        self.page_content = page_content
        self.metadata = metadata or {}

# 导入必要的库
try:
    import sentence_transformers
    print(f"成功导入sentence_transformers库，版本: {sentence_transformers.__version__}")
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"导入sentence_transformers失败: {e}")
    DEPENDENCIES_AVAILABLE = False

# 导入模型
try:
    from .models import Source
except ImportError:
    # 如果作为独立脚本运行
    from models import Source

class RAGEngine:
    """RAG检索引擎类"""
    
    def __init__(self, embeddings_dir: Optional[str] = None):
        """
        初始化RAG引擎
        
        Args:
            embeddings_dir: 向量嵌入目录路径
        """
        # 获取向量嵌入目录
        if embeddings_dir is None:
            embeddings_dir = os.getenv("VECTOR_DB_PATH", "./data/embeddings")
        
        self.embeddings_dir = Path(embeddings_dir)
        
        # 获取嵌入模型设置
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        
        # 初始化嵌入模型
        self.embedding_function = None
        
        if self.embedding_model_name == "SimpleModel":
            # 使用简单词袋模型
            print("使用简单词袋模型作为嵌入方法")
            self.embedding_function = SimpleBOWEmbeddings()
        else:
            # 尝试直接使用sentence_transformers
            try:
                print(f"尝试加载sentence_transformers模型: {self.embedding_model_name}")
                from sentence_transformers import SentenceTransformer
                
                # 配置缓存路径确保使用本地缓存
                cache_dir = os.path.join(os.getcwd(), 'models_cache')
                os.makedirs(cache_dir, exist_ok=True)
                print(f"使用本地模型缓存目录: {cache_dir}")
                
                model = SentenceTransformer(self.embedding_model_name, cache_folder=cache_dir)
                print("成功加载sentence_transformers模型")
                
                # 创建自定义嵌入函数
                class CustomEmbeddings:
                    def __init__(self, model):
                        self.model = model
                    
                    def embed_documents(self, texts):
                        embeddings = self.model.encode(texts)
                        # 确保返回二维列表格式
                        if isinstance(embeddings, np.ndarray):
                            embeddings = embeddings.tolist()
                        # 确保是嵌套列表格式
                        if isinstance(embeddings, list) and embeddings and not isinstance(embeddings[0], list):
                            return [embeddings]
                        return embeddings
                    
                    def embed_query(self, text):
                        embedding = self.model.encode(text)
                        # 确保返回一维列表格式
                        if isinstance(embedding, np.ndarray):
                            embedding = embedding.tolist()
                        # 确保是一维列表
                        if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
                            return embedding[0]
                        return embedding
                
                self.embedding_function = CustomEmbeddings(model)
                print("成功创建自定义嵌入函数")
            except Exception as e:
                print(f"加载sentence_transformers模型失败: {e}")
                print("使用简单词袋模型作为备选方案")
                self.embedding_function = SimpleBOWEmbeddings()
        
        # 初始化向量存储
        try:
            if self.embeddings_dir.exists():
                try:
                    # 尝试导入并使用Chroma
                    from langchain_community.vectorstores import Chroma
                    
                    # 先测试嵌入函数
                    test_text = "这是一个测试文本"
                    test_embedding = self.embedding_function.embed_query(test_text)
                    print(f"测试嵌入向量类型: {type(test_embedding)}")
                    print(f"测试嵌入向量形状: {len(test_embedding)}")
                    
                    self.vectorstore = Chroma(
                        persist_directory=str(self.embeddings_dir),
                        embedding_function=self.embedding_function
                    )
                    print(f"已加载Chroma向量数据库: {self.embeddings_dir}")
                except Exception as e:
                    print(f"加载Chroma失败，使用简单向量存储: {e}")
                    self.vectorstore = SimpleVectorStore(
                        persist_directory=str(self.embeddings_dir),
                        embedding_function=self.embedding_function
                    )
            else:
                print(f"警告: 向量数据库目录不存在: {self.embeddings_dir}")
                print("系统将创建一个空的向量数据库。请先运行数据处理脚本生成嵌入。")
                # 创建一个空的向量存储
                self.vectorstore = SimpleVectorStore(
                    persist_directory=str(self.embeddings_dir),
                    embedding_function=self.embedding_function
                )
                self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"初始化向量数据库失败: {e}")
            print("使用简单向量存储作为备选方案")
            self.vectorstore = SimpleVectorStore(
                persist_directory=str(self.embeddings_dir),
                embedding_function=self.embedding_function
            )
    
    def get_knowledge_base_status(self) -> Dict[str, Any]:
        """
        获取知识库状态信息
        
        Returns:
            包含知识库统计信息的字典
        """
        # 获取集合信息
        collection = self.vectorstore._collection
        
        # 获取文档数量
        count = collection.count()
        
        # 获取所有文档的元数据
        if count > 0:
            results = collection.get()
            metadatas = results["metadatas"]
            
            # 提取唯一文档标题计算文档数量
            unique_titles = set()
            for metadata in metadatas:
                if metadata and "title" in metadata:
                    unique_titles.add(metadata["title"])
            
            document_count = len(unique_titles)
        else:
            document_count = 0
        
        # 获取最后更新时间
        last_updated = "从未"
        if self.embeddings_dir.exists():
            try:
                # 尝试获取目录的最后修改时间
                last_modified = os.path.getmtime(self.embeddings_dir)
                last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_modified))
            except Exception:
                pass
        
        return {
            "document_count": document_count,
            "chunk_count": count,
            "embedding_model": self.embedding_model_name,
            "last_updated": last_updated
        }
    
    def retrieve(self, 
                query: str, 
                max_sources: int = 5, 
                similarity_threshold: float = 0.2
               ) -> Tuple[str, List[Source]]:
        """
        检索与查询相关的文档
        
        Args:
            query: 用户查询
            max_sources: 最大返回源数量
            similarity_threshold: 相似度阈值，低于此值的文档将被过滤
            
        Returns:
            包含检索结果上下文的字符串和来源列表
        """
        # 检查向量存储是否为空
        if self.vectorstore._collection.count() == 0:
            return "知识库为空，请先导入数据。", []
        
        try:
            # 执行相似性搜索
            results = self.vectorstore.similarity_search_with_relevance_scores(
                query, 
                k=max_sources * 3
            )
            
            print(f"\n=== 检索查询: {query} ===")
            print(f"检索到 {len(results)} 个初始结果")
            
            # 过滤相关性低的结果
            filtered_results = []
            for doc, score in results:
                if score >= similarity_threshold:
                    filtered_results.append((doc, score))
                    
            print(f"过滤后剩余 {len(filtered_results)} 个结果（相似度阈值: {similarity_threshold}）")
            
            # 如果没有找到相关结果
            if not filtered_results:
                return "未找到与查询相关的信息。", []
            
            # 限制返回结果数量
            filtered_results = filtered_results[:max_sources]
            
            # 构建上下文信息和来源列表
            context_parts = []
            sources = []
            
            for i, (doc, score) in enumerate(filtered_results):
                # 打印检索结果信息
                title = doc.metadata.get("title", "未知标题")
                print(f"结果 {i+1}: {title} (相关度: {score:.4f})")
                
                # 添加文档内容到上下文
                context_parts.append(f"[{i+1}] {doc.page_content}")
                
                # 提取元数据
                metadata = doc.metadata
                title = metadata.get("title", "未知标题")
                authors = metadata.get("authors", "")
                year = metadata.get("year", "")
                publication = metadata.get("publication", "")
                doi = metadata.get("doi", "")
                url = metadata.get("url", "")
                
                # 创建来源信息
                source = Source(
                    id=i+1,
                    title=title,
                    authors=authors,
                    year=year,
                    publication=publication,
                    relevance=round(score * 100, 2),
                    doi=doi,
                    url=url
                )
                sources.append(source)
            
            # 合并上下文
            context = "\n\n".join(context_parts)
            print(f"生成的上下文长度: {len(context)} 字符")
            
            return context, sources
        
        except Exception as e:
            print(f"检索错误: {e}")
            return f"检索过程中出错: {str(e)}", []

# 测试代码
if __name__ == "__main__":
    print("RAG引擎测试")
    try:
        engine = RAGEngine()
        status = engine.get_knowledge_base_status()
        print(f"知识库状态: {status}")
        
        if status["chunk_count"] > 0:
            # 进行测试查询
            context, sources = engine.retrieve("测试查询")
            print(f"找到 {len(sources)} 个结果")
            for i, source in enumerate(sources):
                print(f"结果 {i+1}: {source.title} (相关度: {source.relevance:.2f})")
    except Exception as e:
        print(f"测试过程中出错: {e}") 
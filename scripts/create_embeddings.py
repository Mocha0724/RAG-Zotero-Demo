#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量嵌入生成脚本
用于将文献数据处理并生成向量嵌入，构建知识库
"""

import os
import sys
import json
import argparse
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

# 导入必要的库
try:
    # 首先尝试直接导入sentence_transformers
    import sentence_transformers
    print(f"成功导入sentence_transformers库，版本: {sentence_transformers.__version__}")
    
    # 导入langchain相关库
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        LANGCHAIN_AVAILABLE = True
        print("成功导入LangChain相关库")
    except ImportError as e:
        print(f"导入LangChain相关库失败: {e}")
        LANGCHAIN_AVAILABLE = False
except ImportError as e:
    print(f"导入sentence_transformers失败: {e}")
    LANGCHAIN_AVAILABLE = False


class DocumentProcessor:
    """文档处理和向量嵌入生成类"""
    
    def __init__(self, input_dir: str, output_dir: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化文档处理器
        
        Args:
            input_dir: 处理过的文献数据目录
            output_dir: 向量嵌入输出目录
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 获取嵌入模型设置
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        print(f"使用嵌入模型: {self.embedding_model_name}")
        
        # 尝试多种方法初始化嵌入模型
        self.embedding_function = None
        
        # 方法1: 尝试使用LangChain的HuggingFaceEmbeddings
        if LANGCHAIN_AVAILABLE:
            try:
                self.embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
                print("成功使用LangChain初始化HuggingFace嵌入模型")
                return
            except Exception as e:
                print(f"使用LangChain初始化HuggingFace嵌入模型失败: {e}")
        
        # 方法2: 尝试直接使用sentence_transformers
        try:
            print("尝试直接使用sentence_transformers...")
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.embedding_model_name)
            print("成功加载sentence_transformers模型")
            
            # 创建自定义嵌入函数
            class CustomEmbeddings:
                def __init__(self, model):
                    self.model = model
                
                def embed_documents(self, texts):
                    return self.model.encode(texts)
                
                def embed_query(self, text):
                    return self.model.encode([text])[0]
            
            self.embedding_function = CustomEmbeddings(model)
            print("成功创建自定义嵌入函数")
            return
        except Exception as e:
            print(f"使用SentenceTransformer直接加载模型失败: {e}")
        
        # 方法3: 使用简单的词袋模型作为最后的备选方案
        print("使用简单词袋模型作为备选方案")
        self.embedding_function = SimpleBOWEmbeddings()
        print("警告: 使用的是简单词袋模型，而非深度学习模型，检索质量可能较低")
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """加载处理过的文献数据"""
        input_file = self.input_dir / "processed_documents.json"
        if not input_file.exists():
            raise FileNotFoundError(f"找不到处理过的文献数据文件：{input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        print(f"已加载{len(documents)}条文献记录")
        return documents
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理文档并分块
        
        Args:
            documents: 文献数据列表
            
        Returns:
            分块后的文档列表
        """
        print("开始处理文档...")
        
        # 创建文本分割器
        if LANGCHAIN_AVAILABLE:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        else:
            # 简单的文本分割器作为备选
            class SimpleTextSplitter:
                def __init__(self, chunk_size, chunk_overlap):
                    self.chunk_size = chunk_size
                    self.chunk_overlap = chunk_overlap
                
                def split_text(self, text):
                    # 按段落分割
                    paragraphs = text.split("\n\n")
                    chunks = []
                    current_chunk = ""
                    
                    for para in paragraphs:
                        if len(current_chunk) + len(para) <= self.chunk_size:
                            current_chunk += para + "\n\n"
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = para + "\n\n"
                    
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # 如果没有足够的段落，则按句子分割
                    if not chunks:
                        sentences = text.split(". ")
                        current_chunk = ""
                        
                        for sentence in sentences:
                            if len(current_chunk) + len(sentence) <= self.chunk_size:
                                current_chunk += sentence + ". "
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                current_chunk = sentence + ". "
                        
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                    
                    # 如果仍然没有足够的块，则按单词分割
                    if not chunks:
                        words = text.split()
                        current_chunk = ""
                        
                        for word in words:
                            if len(current_chunk) + len(word) <= self.chunk_size:
                                current_chunk += word + " "
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                current_chunk = word + " "
                        
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                    
                    return chunks
            
            text_splitter = SimpleTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            print("使用简单文本分割器（LangChain不可用）")
        
        processed_chunks = []
        
        for doc in tqdm(documents, desc="处理文档"):
            # 准备完整文本（结合标题、摘要和全文）
            title = doc.get('title', '')
            abstract = doc.get('abstract', '')
            content = doc.get('content', '')
            
            # 合并作者信息
            authors = ', '.join(doc.get('authors', []))
            
            # 其他元数据
            year = doc.get('year', '')
            publication = doc.get('publication', '')
            doi = doc.get('doi', '')
            url = doc.get('url', '')
            
            # 构建完整文本
            full_text = f"标题: {title}\n\n"
            
            if authors:
                full_text += f"作者: {authors}\n\n"
            
            if year:
                full_text += f"年份: {year}\n\n"
                
            if publication:
                full_text += f"出版物: {publication}\n\n"
                
            if abstract:
                full_text += f"摘要: {abstract}\n\n"
                
            if content:
                full_text += f"全文内容: {content}\n\n"
                
            if doi or url:
                full_text += "参考链接:\n"
                if doi:
                    full_text += f"DOI: {doi}\n"
                if url:
                    full_text += f"URL: {url}\n"
            
            # 分割文本
            if full_text.strip():
                chunks = text_splitter.split_text(full_text)
                
                # 为每个分块创建记录
                for i, chunk in enumerate(chunks):
                    chunk_doc = {
                        "id": f"{doc.get('id', '')}-{i}",
                        "text": chunk,
                        "metadata": {
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "publication": publication,
                            "doi": doi,
                            "url": url,
                            "source": doc.get('source', ''),
                            "chunk_id": i,
                            "total_chunks": len(chunks)
                        }
                    }
                    processed_chunks.append(chunk_doc)
        
        print(f"文档处理完成，生成了{len(processed_chunks)}个文本块")
        return processed_chunks
    
    def create_embeddings(self, chunks: List[Dict[str, Any]]) -> None:
        """
        为文本块创建向量嵌入并保存到向量数据库
        
        Args:
            chunks: 文本块列表
        """
        print("开始创建向量嵌入...")
        
        # 准备文本和元数据
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]
        
        total_chunks = len(chunks)
        print(f"总共需要处理 {total_chunks} 个文本块")
        
        # 创建向量存储
        start_time = time.time()
        
        try:
            # 分批处理，无论使用哪种方式
            batch_size = 50  # 更小的批次大小，减少内存使用
            print(f"使用批处理方式，每批 {batch_size} 个文本块")
            
            if LANGCHAIN_AVAILABLE:
                # 使用Chroma创建向量存储
                try:
                    # 创建空的Chroma实例
                    if os.path.exists(str(self.output_dir)):
                        import shutil
                        print(f"检测到已存在的向量存储目录: {self.output_dir}")
                        print("将清空并重新创建...")
                        shutil.rmtree(str(self.output_dir))
                    
                    os.makedirs(str(self.output_dir), exist_ok=True)
                    
                    from langchain_community.vectorstores import Chroma
                    print("初始化Chroma向量数据库...")
                    vectorstore = Chroma(
                        embedding_function=self.embedding_function,
                        persist_directory=str(self.output_dir)
                    )
                    
                    # 分批添加文档
                    for i in range(0, total_chunks, batch_size):
                        batch_end = min(i + batch_size, total_chunks)
                        batch_texts = texts[i:batch_end]
                        batch_metadatas = metadatas[i:batch_end]
                        batch_ids = ids[i:batch_end]
                        
                        # 显示进度
                        progress = (i / total_chunks) * 100
                        print(f"批次 {i//batch_size + 1}/{(total_chunks-1)//batch_size + 1} ({progress:.1f}%)")
                        print(f"正在处理第 {i+1} 到 {batch_end} 个文本块...")
                        
                        # 计时
                        batch_start = time.time()
                        
                        # 添加文档
                        vectorstore.add_texts(
                            texts=batch_texts,
                            metadatas=batch_metadatas,
                            ids=batch_ids
                        )
                        
                        # 显示本批次用时
                        batch_end_time = time.time()
                        batch_time = batch_end_time - batch_start
                        print(f"批次完成，用时: {batch_time:.2f}秒")
                        
                        # 计算预计剩余时间
                        processed = batch_end
                        remaining = total_chunks - processed
                        avg_time_per_batch = batch_time
                        est_time_remaining = (remaining / batch_size) * avg_time_per_batch
                        
                        # 格式化为时分秒
                        hours, remainder = divmod(est_time_remaining, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        
                        print(f"预计剩余时间: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒")
                        print("-" * 50)
                    
                    # 持久化存储
                    print("正在持久化存储...")
                    vectorstore.persist()
                    print("持久化完成")
                    
                except Exception as chroma_error:
                    print(f"使用Chroma创建向量存储失败: {chroma_error}")
                    print("将使用简单JSON文件存储向量作为备选方案")
                    raise
            
            # 备选方案：创建简单的向量存储（JSON文件）
            if not LANGCHAIN_AVAILABLE or 'chroma_error' in locals():
                print("使用简单JSON文件存储向量")
                all_embeddings = []
                
                for i in range(0, total_chunks, batch_size):
                    batch_end = min(i + batch_size, total_chunks)
                    batch_texts = texts[i:batch_end]
                    
                    # 显示进度
                    progress = (i / total_chunks) * 100
                    print(f"批次 {i//batch_size + 1}/{(total_chunks-1)//batch_size + 1} ({progress:.1f}%)")
                    print(f"正在处理第 {i+1} 到 {batch_end} 个文本块...")
                    
                    # 计时
                    batch_start = time.time()
                    
                    # 生成嵌入
                    print("生成嵌入向量...")
                    batch_embeddings = self.embedding_function.embed_documents(batch_texts)
                    
                    # 显示本批次用时
                    batch_end_time = time.time()
                    batch_time = batch_end_time - batch_start
                    print(f"批次完成，用时: {batch_time:.2f}秒")
                    
                    # 计算预计剩余时间
                    processed = batch_end
                    remaining = total_chunks - processed
                    avg_time_per_batch = batch_time
                    est_time_remaining = (remaining / batch_size) * avg_time_per_batch
                    
                    # 格式化为时分秒
                    hours, remainder = divmod(est_time_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    print(f"预计剩余时间: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒")
                    print("-" * 50)
                    
                    # 保存嵌入
                    all_embeddings.extend(batch_embeddings)
                
                print("所有嵌入向量生成完毕，构建向量数据...")
                
                # 构建完整的向量数据
                vector_data = []
                for i, (text, metadata, id, embedding) in enumerate(zip(texts, metadatas, ids, all_embeddings)):
                    if i % 1000 == 0:  # 每1000个显示一次进度
                        print(f"正在构建向量数据: {i}/{total_chunks}")
                    
                    vector_data.append({
                        "id": id,
                        "text": text,
                        "metadata": metadata,
                        "embedding": embedding
                    })
                
                # 保存为JSON文件
                print("正在保存嵌入数据到文件...")
                output_file = self.output_dir / "embeddings.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(vector_data, f, ensure_ascii=False)
                print(f"嵌入数据已保存至: {output_file}")
                
                # 创建简单的索引文件用于搜索
                print("正在创建索引文件...")
                self._create_simple_index(vector_data)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # 格式化为时分秒
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"向量嵌入创建完成！")
            print(f"总耗时: {int(hours)}小时 {int(minutes)}分钟 {int(seconds)}秒")
            print(f"向量数据已保存至: {self.output_dir}")
            
        except Exception as e:
            print(f"创建向量嵌入时出错: {e}")
            print("\n可能的解决方案:")
            print("1. 检查嵌入模型是否正确加载")
            print("2. 尝试使用不同的嵌入模型")
            print("3. 确保输出目录可写入")
            print("4. 降低批处理大小来减少内存使用")
            raise
    
    def _create_simple_index(self, vector_data):
        """创建简单的索引文件，用于备选搜索方案"""
        index_file = self.output_dir / "simple_index.json"
        
        index = {
            "metadata": {
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "document_count": len(vector_data),
                "embedding_model": str(self.embedding_model_name)
            },
            "vectors": []
        }
        
        # 只保存ID和向量，减小文件大小
        for item in vector_data:
            index["vectors"].append({
                "id": item["id"],
                "embedding": item["embedding"]
            })
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f)
        
        print(f"创建了简单索引文件: {index_file}")
    
    def run(self) -> None:
        """运行完整的文档处理和嵌入生成流程"""
        print("===== 开始构建知识库 =====")
        
        # 加载文档
        documents = self.load_documents()
        
        # 处理文档并分块
        chunks = self.process_documents(documents)
        
        # 创建嵌入并保存
        self.create_embeddings(chunks)
        
        print("===== 知识库构建完成 =====")
        
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文献数据向量嵌入生成工具")
    parser.add_argument('--input-dir', default='data/processed', help='处理过的文献数据目录')
    parser.add_argument('--output-dir', default='data/embeddings', help='向量嵌入输出目录')
    parser.add_argument('--chunk-size', type=int, default=1000, help='文本分块大小')
    parser.add_argument('--chunk-overlap', type=int, default=200, help='文本分块重叠大小')
    args = parser.parse_args()
    
    try:
        processor = DocumentProcessor(
            args.input_dir, 
            args.output_dir,
            args.chunk_size,
            args.chunk_overlap
        )
        processor.run()
    except Exception as e:
        print(f"处理出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
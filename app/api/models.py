#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API数据模型定义
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    """对话消息模型"""
    role: str = Field(..., description="消息角色，'user'或'assistant'")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str = Field(..., description="用户的当前查询")
    history: List[Message] = Field(default_factory=list, description="历史对话记录")
    max_sources: int = Field(default=5, description="最大引用源数量")
    similarity_threshold: float = Field(default=0.6, description="相似度阈值，用于过滤不相关内容")

class Source(BaseModel):
    """引用源模型"""
    title: str = Field(..., description="文献标题")
    authors: str = Field(default="", description="作者")
    year: str = Field(default="", description="出版年份")
    publication: str = Field(default="", description="出版物")
    doi: str = Field(default="", description="DOI")
    url: str = Field(default="", description="URL")
    text: str = Field(default="", description="引用的文本片段")
    score: float = Field(default=0.0, description="相似度得分")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str = Field(..., description="回答内容")
    sources: List[Source] = Field(default_factory=list, description="引用源列表")

class ZoteroCollectionItem(BaseModel):
    """Zotero集合项目模型"""
    id: str = Field(..., description="项目ID")
    title: str = Field(..., description="标题")
    type: str = Field(..., description="类型")

class KnowledgeBaseStatus(BaseModel):
    """知识库状态模型"""
    document_count: int = Field(..., description="文档数量")
    chunk_count: int = Field(..., description="文本块数量")
    embedding_model: str = Field(..., description="嵌入模型")
    last_updated: str = Field(..., description="最后更新时间")
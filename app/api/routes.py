#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API路由定义
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from .models import ChatRequest, ChatResponse, KnowledgeBaseStatus
from .rag import RAGEngine
from .llm import DeepSeekLLM

# 创建路由器
router = APIRouter()

# 创建RAG引擎实例（懒加载）
_rag_engine = None

def get_rag_engine():
    """获取RAG引擎实例（单例模式）"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine

# 创建LLM实例（懒加载）
_llm = None

def get_llm():
    """获取LLM实例（单例模式）"""
    global _llm
    if _llm is None:
        try:
            _llm = DeepSeekLLM()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"初始化LLM失败: {str(e)}")
    return _llm

@router.get("/")
async def root():
    """API根路由"""
    return {"message": "欢迎使用Zotero RAG API"}

@router.get("/status", response_model=KnowledgeBaseStatus)
async def get_status(rag_engine: RAGEngine = Depends(get_rag_engine)):
    """获取知识库状态"""
    try:
        status = rag_engine.get_knowledge_base_status()
        return KnowledgeBaseStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库状态失败: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine),
    llm: DeepSeekLLM = Depends(get_llm)
):
    """
    处理聊天请求
    
    Args:
        request: 聊天请求
        
    Returns:
        包含回答和引用源的响应
    """
    try:
        # 获取查询和历史
        query = request.query
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]
        mode = request.mode
        
        # 根据模式决定是否使用RAG检索
        if mode == "rag":
            # 从知识库中检索相关文档
            context, sources = rag_engine.retrieve(
                query=query,
                max_sources=request.max_sources,
                similarity_threshold=request.similarity_threshold
            )
            
            # 生成回答
            answer = llm.generate_answer(
                query=query, 
                context=context, 
                history=history,
                mode="rag"
            )
            
            # 返回响应
            return ChatResponse(answer=answer, sources=sources)
        else:
            # 纯对话模式，不使用知识库检索
            answer = llm.generate_answer(
                query=query, 
                context=None, 
                history=history,
                mode="chat"
            )
            
            # 返回响应（没有引用源）
            return ChatResponse(answer=answer, sources=[])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理聊天请求失败: {str(e)}") 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大语言模型接口
用于与DeepSeek API通信
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class DeepSeekLLM:
    """DeepSeek大语言模型接口类"""
    
    def __init__(self):
        """初始化DeepSeek LLM接口"""
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未设置DEEPSEEK_API_KEY环境变量")
        
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.api_base_url = "https://api.deepseek.com/v1"
        
        # 构建API URL
        self.api_url = f"{self.api_base_url}/chat/completions"
        
        # 设置请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_answer(self, 
                         query: str, 
                         context: str, 
                         history: Optional[List[Dict[str, str]]] = None
                        ) -> str:
        """
        生成回答
        
        Args:
            query: 用户查询
            context: 检索到的上下文信息
            history: 对话历史
            
        Returns:
            生成的回答
        """
        if history is None:
            history = []
        
        # 构建系统提示
        system_prompt = """你是一个基于RAG(检索增强生成)的学术助手，能够提供准确的、有根据的回答。
请基于提供的学术文献信息回答问题。如果检索到的信息不足以回答问题，请清楚地说明。
回答应当简洁明了，并忠实于检索到的内容，避免编造或推测信息。
仅在客观回答问题即可，无需介绍自己或重复问题。
"""
        
        # 构建检索上下文提示
        context_prompt = f"""以下是与问题相关的学术文献信息：

{context}

请根据以上信息回答问题，不要引用未提供的信息。如果提供的信息不足，请说明："基于所提供的信息，无法完整回答此问题。"
"""
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加检索上下文和当前查询
        messages.append({"role": "user", "content": context_prompt})
        messages.append({"role": "user", "content": query})
        
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # 较低的温度以获得更确定性的回答
            "max_tokens": 2000
        }
        
        try:
            # 发送请求
            response = requests.post(self.api_url, headers=self.headers, json=data)
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"]
                return answer
            else:
                error_msg = f"API请求失败: HTTP {response.status_code} - {response.text}"
                print(error_msg)
                return f"很抱歉，我遇到了技术问题。错误信息: {error_msg}"
                
        except Exception as e:
            error_msg = str(e)
            print(f"API调用出错: {error_msg}")
            return f"很抱歉，我遇到了技术问题。错误信息: {error_msg}" 
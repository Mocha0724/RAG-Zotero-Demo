#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API主入口文件
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入路由
from .routes import router

# 创建FastAPI实例
app = FastAPI(
    title="Zotero RAG API",
    description="基于Zotero文献库的检索增强生成API",
    version="0.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，也可以设置为特定域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

# 挂载静态文件
# 将整个app目录作为静态文件目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
app_dir = os.path.join(project_root, "app")
print(f"挂载静态文件目录: {app_dir}")
app.mount("/app", StaticFiles(directory=app_dir), name="app")

# 包含路由
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    """根路由重定向到API文档"""
    return {"message": "欢迎使用Zotero RAG API", "docs_url": "/docs", "web_url": "/app/pages/index.html"}

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", 8000))
    
    uvicorn.run("app.api.main:app", host=host, port=port, reload=True) 
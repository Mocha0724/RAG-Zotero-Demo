#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务器启动脚本
"""

import os
import sys
import argparse
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Zotero RAG Demo服务器")
    parser.add_argument('--host', default=os.getenv('APP_HOST', '127.0.0.1'), help='主机地址')
    parser.add_argument('--port', type=int, default=int(os.getenv('APP_PORT', 8000)), help='端口号')
    parser.add_argument('--reload', action='store_true', help='是否启用热重载（开发模式）')
    args = parser.parse_args()
    
    print(f"启动服务器: {args.host}:{args.port}")
    print("API文档: http://{}:{}/docs".format(args.host, args.port))
    print("Web界面: http://{}:{}/app/pages/index.html".format(args.host, args.port))
    
    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main() 
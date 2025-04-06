#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
环境检查脚本
用于验证RAG Demo的运行环境是否配置正确
"""

import sys
import os
import importlib
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_python_version():
    """检查Python版本"""
    required_version = (3, 8, 0)
    current_version = sys.version_info
    
    if current_version < required_version:
        print(f"❌ Python版本检查失败: 当前版本 {current_version[0]}.{current_version[1]}.{current_version[2]}, "
              f"需要版本 {required_version[0]}.{required_version[1]}.{required_version[2]} 或更高")
        return False
    
    print(f"✅ Python版本: {current_version[0]}.{current_version[1]}.{current_version[2]}")
    return True

def check_dependencies():
    """检查必要的依赖包是否已安装"""
    required_packages = [
        "fastapi", "uvicorn", "pydantic", "python-dotenv", 
        "langchain", "chromadb", "sentence_transformers", 
        "pypdf", "bibtexparser", "tqdm"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 依赖检查失败: 缺少以下包: {', '.join(missing_packages)}")
        print("   请运行 `pip install -r requirements.txt` 安装所有依赖")
        return False
    
    print(f"✅ 必要依赖: 已安装")
    return True

def check_api_key():
    """检查DeepSeek API密钥配置"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ DeepSeek API密钥未配置")
        print("   请在.env文件中设置DEEPSEEK_API_KEY")
        return False
    
    if api_key == "your_deepseek_api_key":
        print("❌ DeepSeek API密钥未更新")
        print("   请将.env文件中的DEEPSEEK_API_KEY更新为您的实际API密钥")
        return False
    
    print("✅ DeepSeek API密钥: 已配置")
    return True

def check_api_connection():
    """检查与DeepSeek API的连接"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key or api_key == "your_deepseek_api_key":
        print("⚠️ 跳过API连接测试: API密钥未正确配置")
        return True  # 跳过测试但不阻止检查流程
    
    try:
        # 简单的API连接测试 (根据DeepSeek API的实际情况可能需要调整)
        # 这里只是一个示例，实际上需要根据DeepSeek的API文档修改
        response = requests.post(
            "https://api.deepseek.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        
        if response.status_code == 200 or response.status_code == 401:
            print("✅ DeepSeek API连接: 成功")
            return True
        else:
            print(f"❌ DeepSeek API连接: 失败 (HTTP状态码: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ DeepSeek API连接: 出错 ({str(e)})")
        return False

def check_file_structure():
    """检查项目文件结构"""
    required_dirs = [
        "app", "app/api", "app/components", "app/pages", "app/utils",
        "data", "data/embeddings", "data/processed", "data/raw",
        "scripts", "notebooks"
    ]
    
    missing_dirs = []
    
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ 文件结构检查失败: 缺少以下目录: {', '.join(missing_dirs)}")
        return False
    
    print("✅ 项目文件结构: 完整")
    return True

def main():
    """主函数"""
    print("\n========== RAG Demo 环境检查 ==========\n")
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_api_key(),
        check_api_connection(),
        check_file_structure()
    ]
    
    if all(checks):
        print("\n✅ 所有检查通过! 环境已正确配置。")
        print("   您可以开始使用RAG Demo了。")
    else:
        print("\n❌ 环境检查未通过。请解决上述问题后再继续。")
    
    print("\n========================================\n")

if __name__ == "__main__":
    main() 
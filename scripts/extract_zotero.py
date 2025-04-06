#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Zotero数据提取脚本
用于从Zotero导出的数据中提取文献信息
支持BibTeX, CSV和RDF格式
可选择从本地文件或通过Zotero API获取数据
"""

import os
import sys
import json
import argparse
import bibtexparser
import csv
import re
import glob
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from tqdm import tqdm
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 尝试导入pyzotero（如果安装）
try:
    from pyzotero import zotero
    ZOTERO_API_AVAILABLE = True
except ImportError:
    ZOTERO_API_AVAILABLE = False

class ZoteroExtractor:
    """Zotero数据提取器类"""
    
    def __init__(self, raw_data_dir: str, output_dir: str):
        """
        初始化Zotero数据提取器
        
        Args:
            raw_data_dir: Zotero导出数据的目录路径
            output_dir: 处理后数据的输出目录路径
        """
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的文件格式
        self.supported_formats = {
            '.bib': self._parse_bibtex,
            '.csv': self._parse_csv,
            '.rdf': self._parse_rdf,
            '.json': self._parse_json
        }
        
        # 存储提取的文献数据
        self.documents = []
    
    def extract_from_files(self) -> List[Dict[str, Any]]:
        """
        从本地文件中提取Zotero数据
        
        Returns:
            包含所有文献数据的列表
        """
        # 找出所有支持的文件
        files = []
        for ext in self.supported_formats:
            files.extend(list(self.raw_data_dir.glob(f"*{ext}")))
        
        if not files:
            print(f"错误: 在{self.raw_data_dir}中未找到支持的Zotero导出文件。")
            print(f"支持的格式: {', '.join(self.supported_formats.keys())}")
            return []
        
        # 处理每个文件
        for file in tqdm(files, desc="处理Zotero文件"):
            ext = file.suffix.lower()
            if ext in self.supported_formats:
                parser = self.supported_formats[ext]
                try:
                    docs = parser(file)
                    self.documents.extend(docs)
                    print(f"已从{file}提取{len(docs)}条文献记录")
                except Exception as e:
                    print(f"处理{file}时出错: {str(e)}")
        
        # 提取PDF全文（如果有）
        self._extract_pdf_content()
        
        # 保存提取的数据
        self._save_documents()
        
        return self.documents
    
    def extract_from_api(self) -> List[Dict[str, Any]]:
        """
        通过Zotero API提取数据
        
        Returns:
            包含所有文献数据的列表
        """
        if not ZOTERO_API_AVAILABLE:
            print("错误: 未安装pyzotero库，无法使用API。请运行`pip install pyzotero`")
            return []
        
        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
        
        if not api_key or not library_id:
            print("错误: 未配置Zotero API密钥或库ID。请在.env文件中设置ZOTERO_API_KEY和ZOTERO_LIBRARY_ID")
            return []
        
        try:
            zot = zotero.Zotero(library_id, library_type, api_key)
            items = zot.everything(zot.top())
            
            # 处理每个项目
            for item in tqdm(items, desc="从Zotero API获取数据"):
                if item['data']['itemType'] == 'attachment':
                    continue  # 跳过附件
                
                doc = self._process_api_item(item)
                if doc:
                    self.documents.append(doc)
            
            # 保存提取的数据
            self._save_documents()
            
            return self.documents
            
        except Exception as e:
            print(f"使用Zotero API时出错: {str(e)}")
            return []
    
    def _process_api_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理从API获取的项目"""
        try:
            data = item['data']
            
            # 基本检查，确保是文献类型
            if data['itemType'] not in ['journalArticle', 'book', 'bookSection', 'conferencePaper']:
                return None
            
            doc = {
                'id': data.get('key', ''),
                'title': data.get('title', ''),
                'abstract': data.get('abstractNote', ''),
                'authors': [],
                'year': data.get('date', '')[:4] if data.get('date') else '',
                'publication': data.get('publicationTitle', ''),
                'doi': data.get('DOI', ''),
                'url': data.get('url', ''),
                'tags': [tag['tag'] for tag in data.get('tags', [])],
                'content': '',
                'source': 'zotero_api'
            }
            
            # 提取作者
            creators = data.get('creators', [])
            for creator in creators:
                if creator.get('creatorType') == 'author':
                    name_parts = [creator.get('lastName', ''), creator.get('firstName', '')]
                    name = ' '.join([part for part in name_parts if part])
                    if name:
                        doc['authors'].append(name)
            
            return doc
            
        except Exception as e:
            print(f"处理API项目时出错: {str(e)}")
            return None
    
    def _parse_bibtex(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析BibTeX文件"""
        with open(file_path, 'r', encoding='utf-8') as bibtex_file:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_database = bibtexparser.load(bibtex_file, parser)
        
        documents = []
        for entry in bib_database.entries:
            doc = {
                'id': entry.get('ID', ''),
                'title': entry.get('title', '').replace('{', '').replace('}', ''),
                'abstract': entry.get('abstract', ''),
                'authors': self._parse_bibtex_authors(entry.get('author', '')),
                'year': entry.get('year', ''),
                'publication': entry.get('journal', ''),
                'doi': entry.get('doi', ''),
                'url': entry.get('url', ''),
                'tags': [],
                'content': '',
                'source': 'bibtex',
                'file': entry.get('file', '')  # 尝试获取文件路径信息（可能在BibTeX中）
            }
            documents.append(doc)
        
        return documents
    
    def _parse_bibtex_authors(self, author_str: str) -> List[str]:
        """解析BibTeX作者字段"""
        if not author_str:
            return []
        
        # 按"and"分割，并去除大括号
        authors = []
        for author in author_str.split(' and '):
            author = author.replace('{', '').replace('}', '')
            if ',' in author:
                # 格式: 姓,名
                last_name, first_name = author.split(',', 1)
                author = f"{first_name.strip()} {last_name.strip()}"
            authors.append(author.strip())
        
        return authors
    
    def _parse_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析CSV文件"""
        documents = []
        with open(file_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                doc = {
                    'id': row.get('Key', ''),
                    'title': row.get('Title', ''),
                    'abstract': row.get('Abstract Note', ''),
                    'authors': [a.strip() for a in row.get('Author', '').split(';') if a.strip()],
                    'year': row.get('Publication Year', ''),
                    'publication': row.get('Publication Title', ''),
                    'doi': row.get('DOI', ''),
                    'url': row.get('Url', ''),
                    'tags': [t.strip() for t in row.get('Manual Tags', '').split(';') if t.strip()],
                    'content': '',
                    'source': 'csv',
                    'file': row.get('File Attachments', '')
                }
                documents.append(doc)
        
        return documents
    
    def _parse_rdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析RDF文件（简化版本）"""
        # 注意: 完整的RDF解析相对复杂，这里仅简单实现
        # 实际项目中可能需要使用专门的RDF库
        try:
            import xml.etree.ElementTree as ET
            
            documents = []
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 查找所有文献条目
            for item in root.findall('.//{http://www.zotero.org/namespaces/export#}Item'):
                if item.get('itemType') in ['journalArticle', 'book', 'bookSection', 'conferencePaper']:
                    doc = {
                        'id': item.get('id', ''),
                        'title': '',
                        'abstract': '',
                        'authors': [],
                        'year': '',
                        'publication': '',
                        'doi': '',
                        'url': '',
                        'tags': [],
                        'content': '',
                        'source': 'rdf'
                    }
                    
                    # 提取字段
                    for field in item:
                        tag = field.tag.split('}')[-1]
                        if tag == 'title':
                            doc['title'] = field.text or ''
                        elif tag == 'abstract':
                            doc['abstract'] = field.text or ''
                        # 其他字段可以类似处理...
                    
                    documents.append(doc)
            
            return documents
            
        except ImportError:
            print("警告: 未能解析RDF文件，请确保安装了xml模块")
            return []
        except Exception as e:
            print(f"解析RDF文件时出错: {str(e)}")
            return []
    
    def _parse_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        
        documents = []
        for item in data:
            if isinstance(item, dict):
                doc = {
                    'id': item.get('id', item.get('key', '')),
                    'title': item.get('title', ''),
                    'abstract': item.get('abstract', item.get('abstractNote', '')),
                    'authors': [],
                    'year': '',
                    'publication': item.get('publication', item.get('publicationTitle', '')),
                    'doi': item.get('doi', item.get('DOI', '')),
                    'url': item.get('url', ''),
                    'tags': [],
                    'content': '',
                    'source': 'json'
                }
                
                # 提取作者
                authors = item.get('authors', item.get('creators', []))
                if isinstance(authors, list):
                    for author in authors:
                        if isinstance(author, dict):
                            name_parts = []
                            if 'firstName' in author and author['firstName']:
                                name_parts.append(author['firstName'])
                            if 'lastName' in author and author['lastName']:
                                name_parts.append(author['lastName'])
                            if name_parts:
                                doc['authors'].append(' '.join(name_parts))
                        elif isinstance(author, str):
                            doc['authors'].append(author)
                
                # 提取年份
                date = item.get('date', '')
                if date:
                    year_match = re.search(r'\d{4}', date)
                    if year_match:
                        doc['year'] = year_match.group(0)
                
                # 提取标签
                tags = item.get('tags', [])
                if isinstance(tags, list):
                    for tag in tags:
                        if isinstance(tag, dict) and 'tag' in tag:
                            doc['tags'].append(tag['tag'])
                        elif isinstance(tag, str):
                            doc['tags'].append(tag)
                
                documents.append(doc)
        
        return documents
    
    def _extract_pdf_content(self):
        """从PDF文件中提取全文内容"""
        try:
            from pypdf import PdfReader
            
            print("开始提取PDF全文内容...")
            
            # 1. 首先检查Zotero默认的files文件夹结构
            files_dir = self.raw_data_dir / "files"
            if files_dir.exists() and files_dir.is_dir():
                print(f"找到Zotero files文件夹: {files_dir}")
                
                # 查找所有PDF文件（可能在子文件夹中）
                pdf_files = list(files_dir.glob("**/*.pdf"))
                print(f"在files文件夹中找到{len(pdf_files)}个PDF文件")
                
                if pdf_files:
                    self._process_pdf_files(pdf_files)
                    return
            
            # 2. 如果没有找到files文件夹或其中没有PDF，则查找原目录中的PDF
            pdf_files = list(self.raw_data_dir.glob("*.pdf"))
            if pdf_files:
                print(f"在{self.raw_data_dir}中找到{len(pdf_files)}个PDF文件")
                self._process_pdf_files(pdf_files)
                return
            
            # 3. 尝试从BibTeX文件的file字段获取路径信息
            pdf_paths_from_bibtex = self._get_pdf_paths_from_bibtex()
            if pdf_paths_from_bibtex:
                print(f"从BibTeX获取到{len(pdf_paths_from_bibtex)}个PDF文件路径")
                self._process_pdf_files(pdf_paths_from_bibtex)
                return
            
            print("未找到PDF文件，跳过全文提取")
            
        except ImportError:
            print("警告: 未安装pypdf库，无法提取PDF全文。请运行`pip install pypdf`")
            
    def _get_pdf_paths_from_bibtex(self) -> List[Path]:
        """从BibTeX的file字段获取PDF路径"""
        pdf_paths = []
        
        for doc in self.documents:
            if 'file' in doc and doc['file']:
                # 尝试解析file字段（通常格式为 "description:path:type"）
                file_entries = doc['file'].split(';')
                for entry in file_entries:
                    parts = entry.split(':')
                    if len(parts) >= 2:
                        # 后面的部分是路径
                        path_str = ':'.join(parts[1:])
                        # 清理路径
                        path_str = path_str.strip()
                        if path_str.endswith('.pdf'):
                            # 尝试直接使用路径
                            pdf_path = Path(path_str)
                            if not pdf_path.exists():
                                # 尝试相对于raw_data_dir的路径
                                pdf_path = self.raw_data_dir / path_str
                            
                            if pdf_path.exists():
                                pdf_paths.append(pdf_path)
        
        return pdf_paths
            
    def _process_pdf_files(self, pdf_files: List[Path]):
        """处理PDF文件并提取文本"""
        try:
            from pypdf import PdfReader
            
            # 对于每个文档，尝试找到匹配的PDF
            for doc in tqdm(self.documents, desc="提取PDF全文"):
                doc_title = doc.get('title', '').lower()
                if not doc_title:
                    continue
                
                # 简化标题以进行匹配
                simple_title = re.sub(r'[^\w\s]', '', doc_title).lower()
                words = simple_title.split()
                
                best_match = None
                best_score = 0
                
                for pdf_file in pdf_files:
                    pdf_name = pdf_file.stem.lower()
                    
                    # 检查PDF文件名是否包含足够的标题词
                    match_score = sum(1 for word in words if word in pdf_name)
                    if match_score > best_score:
                        best_score = match_score
                        best_match = pdf_file
                
                # 如果有足够的匹配度，提取PDF内容
                if best_match and best_score >= min(3, len(words) // 2):
                    try:
                        # 提取PDF文本
                        reader = PdfReader(best_match)
                        text = ""
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:  # 确保提取的文本不为None
                                text += page_text + "\n"
                        
                        doc['content'] = text.strip()
                        print(f"已为文档《{doc['title']}》提取PDF全文（来自{best_match}）")
                    except Exception as e:
                        print(f"处理PDF文件{best_match}时出错: {str(e)}")
        
        except ImportError:
            print("警告: 未安装pypdf库，无法提取PDF全文。请运行`pip install pypdf`")
    
    def _save_documents(self):
        """保存处理后的文档数据"""
        output_file = self.output_dir / 'processed_documents.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        
        print(f"已将{len(self.documents)}条文献记录保存至{output_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Zotero文献数据提取工具")
    parser.add_argument('--data-dir', default='data/raw', help='Zotero导出数据的目录路径')
    parser.add_argument('--output-dir', default='data/processed', help='处理后数据的输出目录路径')
    parser.add_argument('--api', action='store_true', help='使用Zotero API获取数据')
    args = parser.parse_args()
    
    print("===== Zotero文献数据提取 =====")
    extractor = ZoteroExtractor(args.data_dir, args.output_dir)
    
    if args.api:
        print("使用Zotero API获取数据...")
        documents = extractor.extract_from_api()
    else:
        print(f"从本地文件{args.data_dir}提取数据...")
        documents = extractor.extract_from_files()
    
    print(f"数据提取完成，共{len(documents)}条记录。")

if __name__ == "__main__":
    main() 
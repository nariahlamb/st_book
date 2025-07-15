#!/usr/bin/env python3
"""
文本分割器 - 将小说文本分割为适合处理的文本块
"""

import json
import re
from pathlib import Path
from typing import List, Tuple
from project_config import get_config

class TextSplitter:
    """文本分割器 - 支持按大小和按章节分割"""
    
    def __init__(self):
        self.config = get_config()
        
        # 从配置读取参数
        self.max_chunk_chars = int(self.config.get("text_processing.max_chunk_chars", 30000))
        self.buffer_chars = int(self.config.get("text_processing.buffer_chars", 200))
        self.split_method = self.config.get("text_processing.split_method", "size")
        
        # 章节识别模式
        self.chapter_patterns = self.config.get("text_processing.chapter_patterns", [
            "第[一二三四五六七八九十百千万\\d]+章",
            "第[一二三四五六七八九十百千万\\d]+节",
            "第[一二三四五六七八九十百千万\\d]+回"
        ])
        
        # 输出目录
        self.output_dir = Path(self.config.get("output.chunk_dir", "chunks"))
        self.output_dir.mkdir(exist_ok=True)
    
    def split_novel(self, input_file: str, method: str = None) -> List[str]:
        """分割小说文本
        
        Args:
            input_file: 输入文件路径
            method: 分割方法 ('size' 或 'chapter')
            
        Returns:
            生成的文本块文件路径列表
        """
        if method is None:
            method = self.split_method
            
        print(f"开始分割文本文件: {input_file}")
        print(f"分割方法: {method}")
        print(f"最大块大小: {self.max_chunk_chars} 字符")
        print(f"缓冲区大小: {self.buffer_chars} 字符")
        
        # 读取文本
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"找不到输入文件: {input_file}")
            
        encoding = self.config.get("input.encoding", "utf-8")
        with open(input_path, 'r', encoding=encoding) as f:
            text = f.read()
        
        print(f"原始文本长度: {len(text):,} 字符")
        
        # 根据方法分割
        if method == "chapter":
            chunks = self._split_by_chapters(text)
        else:
            chunks = self._split_by_size(text)
        
        # 保存文本块
        chunk_files = self._save_chunks(chunks)
        
        print(f"分割完成！生成了 {len(chunk_files)} 个文本块")
        print(f"平均块大小: {sum(len(chunk) for chunk in chunks) // len(chunks):,} 字符")
        
        # 保存映射信息
        self._save_mapping(chunk_files, chunks)
        
        return chunk_files
    
    def _split_by_size(self, text: str) -> List[str]:
        """按大小分割文本"""
        chunks = []
        start = 0
        
        while start < len(text):
            # 计算当前块的结束位置
            end = start + self.max_chunk_chars
            
            if end >= len(text):
                # 最后一块
                chunks.append(text[start:])
                break
            
            # 寻找合适的分割点（避免在句子中间分割）
            split_point = self._find_split_point(text, start, end)
            
            # 添加当前块
            chunks.append(text[start:split_point])
            
            # 计算下一块的开始位置（包含缓冲区）
            start = max(split_point - self.buffer_chars, start + 1)
        
        return chunks
    
    def _split_by_chapters(self, text: str) -> List[str]:
        """按章节分割文本"""
        # 合并所有章节模式
        pattern = '|'.join(f'({p})' for p in self.chapter_patterns)
        
        # 查找所有章节标题
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            print("警告: 未找到章节标题，使用按大小分割")
            return self._split_by_size(text)
        
        chunks = []
        
        for i, match in enumerate(matches):
            start = match.start()
            
            # 确定章节结束位置
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)
            
            chapter_text = text[start:end].strip()
            
            # 如果章节太长，进一步分割
            if len(chapter_text) > self.max_chunk_chars:
                sub_chunks = self._split_by_size(chapter_text)
                chunks.extend(sub_chunks)
            else:
                chunks.append(chapter_text)
        
        return chunks
    
    def _find_split_point(self, text: str, start: int, end: int) -> int:
        """寻找合适的分割点"""
        # 优先在段落边界分割
        for i in range(end - 1, start, -1):
            if text[i] == '\n' and text[i-1] == '\n':
                return i
        
        # 其次在句号、问号、感叹号后分割
        for i in range(end - 1, start, -1):
            if text[i] in '。！？':
                return i + 1
        
        # 最后在逗号、分号后分割
        for i in range(end - 1, start, -1):
            if text[i] in '，；':
                return i + 1
        
        # 如果找不到合适的分割点，就在指定位置分割
        return end
    
    def _save_chunks(self, chunks: List[str]) -> List[str]:
        """保存文本块到文件"""
        chunk_files = []
        
        for i, chunk in enumerate(chunks, 1):
            filename = f"chunk_{i:03d}.txt"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(chunk)
            
            chunk_files.append(str(filepath))
        
        return chunk_files
    
    def _save_mapping(self, chunk_files: List[str], chunks: List[str]):
        """保存文本块映射信息"""
        mapping = {
            "total_chunks": len(chunks),
            "total_chars": sum(len(chunk) for chunk in chunks),
            "avg_chunk_size": sum(len(chunk) for chunk in chunks) // len(chunks),
            "chunks": [
                {
                    "file": Path(file).name,
                    "size": len(chunk),
                    "start_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
                }
                for file, chunk in zip(chunk_files, chunks)
            ]
        }
        
        mapping_file = self.output_dir / "mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        print(f"映射信息已保存到: {mapping_file}")
    
    def get_chunk_files(self) -> List[Path]:
        """获取所有文本块文件"""
        return sorted(self.output_dir.glob("chunk_*.txt"))
    
    def get_chunk_count(self) -> int:
        """获取文本块数量"""
        return len(self.get_chunk_files())
    
    def split_text(self):
        """使用配置文件中的源文件进行分割"""
        source_file = self.config.get("input.source_file", "a.txt")
        return self.split_novel(source_file)

if __name__ == "__main__":
    # 测试文本分割器
    splitter = TextSplitter()
    
    # 检查是否有输入文件
    source_file = "a.txt"
    if Path(source_file).exists():
        chunk_files = splitter.split_novel(source_file)
        print(f"\n生成的文本块文件:")
        for file in chunk_files[:5]:  # 只显示前5个
            print(f"  {file}")
        if len(chunk_files) > 5:
            print(f"  ... 还有 {len(chunk_files) - 5} 个文件")
    else:
        print(f"找不到输入文件: {source_file}")
        print("请将小说文本文件命名为 a.txt 并放在当前目录")
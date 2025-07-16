#!/usr/bin/env python3
"""
文本分割器 - 将完整小说文本分割为文本块
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
import json
from datetime import datetime
from project_config import get_config

class TextSplitter:
    """文本分割器"""

    def __init__(self, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        self.config = get_config()
        # 使用新的配置结构
        default_chunk_size = self.config.get('text_processing.max_chunk_chars', 30000)
        default_overlap = self.config.get('text_processing.buffer_chars', 200)

        self.chunk_size: int = chunk_size if chunk_size is not None else int(default_chunk_size)
        self.overlap: int = overlap if overlap is not None else int(default_overlap)

        # 从配置读取输出目录
        self.output_dir = Path(self.config.get('output.chunk_dir', 'chunks'))
        self.output_dir.mkdir(exist_ok=True)

        # 章节模式
        self.chapter_patterns = [
            r'第[一二三四五六七八九十百千万\d]+章',
            r'第[一二三四五六七八九十百千万\d]+节',
            r'第[一二三四五六七八九十百千万\d]+回',
            r'第[一二三四五六七八九十百千万\d]+部分',
            r'Chapter \d+',
            r'章节 \d+'
        ]
    
    def clean_text(self, text: str) -> str:
        """清理文本，保持段落结构"""
        # 移除版权信息和无关内容
        lines = text.split('\n')
        cleaned_lines = []

        skip_patterns = [
            r'┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓',
            r'┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛',
            r'精校小说尽在河洛网',
            r'本电子书由.*整理校对',
            r'版权归原作者所有',
            r'请勿转载',
            r'请勿用于.*商业用途'
        ]

        for line in lines:
            # 保持空行，用于段落分隔
            if not line.strip():
                cleaned_lines.append('')
                continue

            line = line.strip()

            # 跳过版权信息
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line):
                    skip = True
                    break

            if not skip:
                cleaned_lines.append(line)

        # 重新连接，保持原有的换行结构
        return '\n'.join(cleaned_lines)
    
    def split_by_chapters(self, text: str) -> List[Tuple[str, str]]:
        """按章节分割文本"""
        chapters = []
        
        # 章节标题模式
        chapter_pattern = r'^第\s*\d+\s*章\s+(.*)$'
        
        lines = text.split('\n')
        current_title = "开头"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是章节标题
            chapter_match = re.match(chapter_pattern, line)
            if chapter_match:
                # 保存前一章
                if current_content:
                    chapters.append((current_title, '\n'.join(current_content)))
                
                # 开始新章节
                current_title = line
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一章
        if current_content:
            chapters.append((current_title, '\n'.join(current_content)))
        
        return chapters
    
    def split_by_size(self, text: str) -> List[str]:
        """按大小分割文本"""
        chunks = []
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 如果添加这个段落会超过大小限制
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    
                    # 添加重叠内容
                    if self.overlap > 0:
                        overlap_text = current_chunk[-self.overlap:]
                        current_chunk = overlap_text + '\n\n' + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    # 单个段落就超过大小限制，直接添加
                    chunks.append(paragraph)
                    current_chunk = ""
            else:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def split_novel(self, input_file: str, method: str = "size"):
        """分割小说文本"""
        print("="*60)
        print("文本分割器")
        print("="*60)
        
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"错误: 找不到输入文件 {input_file}")
            return
        
        # 读取文本
        print(f"读取文件: {input_file}")
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
        
        # 清理文本
        print("清理文本...")
        cleaned_text = self.clean_text(text)
        print(f"原始长度: {len(text):,} 字符")
        print(f"清理后长度: {len(cleaned_text):,} 字符")
        
        # 分割文本
        print(f"分割方法: {method}")
        
        if method == "chapter":
            # 按章节分割
            chapters = self.split_by_chapters(cleaned_text)
            chunks = [content for _, content in chapters]
            # 构建章节信息
            chapter_info = [
                {
                    "title": title,
                    "number": i + 1
                }
                for i, (title, _) in enumerate(chapters)
            ]
            print(f"分割为 {len(chunks)} 个章节")
        else:
            # 按大小分割
            chunks = self.split_by_size(cleaned_text)
            chapter_info = None  # 按大小分割时没有章节信息
            print(f"分割为 {len(chunks)} 个文本块")

        # 保存文本块
        self.save_chunks(chunks)

        # 生成映射文件（包含时序元数据）
        self.generate_mapping(chunks, method, chapter_info)
        
        print(f"\n="*60)
        print(f"文本分割完成！")
        print(f"生成文本块: {len(chunks)} 个")
        print(f"保存位置: {self.output_dir}")
        print(f"平均长度: {sum(len(chunk) for chunk in chunks) // len(chunks):,} 字符")
        print("="*60)
    
    def save_chunks(self, chunks: List[str]):
        """保存文本块"""
        # 清理输出目录
        for old_file in self.output_dir.glob("chunk_*.txt"):
            old_file.unlink()
        
        # 保存新的文本块
        for i, chunk in enumerate(chunks, 1):
            chunk_file = self.output_dir / f"chunk_{i:03d}.txt"
            
            try:
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                
                print(f"保存: {chunk_file.name} ({len(chunk):,} 字符)")
                
            except Exception as e:
                print(f"保存失败 {chunk_file}: {e}")
    
    def generate_mapping(self, chunks: List[str], method: str, chapter_info: Optional[List[dict]] = None):
        """生成映射文件，包含时序元数据和章节信息"""
        mapping = {
            "method": method,
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "total_chunks": len(chunks),
            "generation_timestamp": json.dumps(datetime.now().isoformat()),
            "chunks": []
        }

        for i, chunk in enumerate(chunks, 1):
            chunk_info = {
                "id": f"chunk_{i:03d}",
                "order": i,  # 时序顺序
                "length": len(chunk),
                "preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
            }

            # 添加章节信息（如果可用）
            if chapter_info and i <= len(chapter_info):
                chapter_data = chapter_info[i-1]
                chunk_info.update({
                    "chapter_title": chapter_data.get("title", f"第{i}部分"),
                    "chapter_number": chapter_data.get("number", i),
                    "estimated_timeline_position": self._estimate_timeline_position(i, len(chunks)),
                    "narrative_context": self._analyze_narrative_context(chunk)
                })
            else:
                # 默认章节信息
                chunk_info.update({
                    "chapter_title": f"第{i}部分",
                    "chapter_number": i,
                    "estimated_timeline_position": self._estimate_timeline_position(i, len(chunks)),
                    "narrative_context": self._analyze_narrative_context(chunk)
                })

            mapping["chunks"].append(chunk_info)

        # 保存映射文件
        mapping_file = self.output_dir / "mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        print(f"生成映射文件: {mapping_file}")
        print(f"包含时序元数据: {len(chunks)} 个文本块")

    def _estimate_timeline_position(self, chunk_index: int, total_chunks: int) -> str:
        """估算文本块在故事时间线中的位置"""
        progress = chunk_index / total_chunks

        if progress <= 0.1:
            return "故事开端"
        elif progress <= 0.3:
            return "情节发展"
        elif progress <= 0.7:
            return "故事高潮"
        elif progress <= 0.9:
            return "情节收束"
        else:
            return "故事结局"

    def _analyze_narrative_context(self, chunk_text: str) -> dict:
        """分析文本块的叙述上下文"""
        context = {
            "has_dialogue": bool(re.search(r'[""].*?[""]|「.*?」', chunk_text)),
            "has_action": bool(re.search(r'(打|击|攻|战|斗|跑|飞|跳)', chunk_text)),
            "has_description": bool(re.search(r'(美丽|壮观|巨大|微小|明亮|黑暗)', chunk_text)),
            "emotional_tone": self._detect_emotional_tone(chunk_text),
            "character_density": len(re.findall(r'[\u4e00-\u9fff]{2,4}(?=说|道|想|看|听)', chunk_text))
        }
        return context

    def _detect_emotional_tone(self, text: str) -> str:
        """检测文本的情感基调"""
        positive_words = ['高兴', '快乐', '兴奋', '满意', '欣喜', '愉悦']
        negative_words = ['愤怒', '悲伤', '恐惧', '绝望', '痛苦', '焦虑']
        neutral_words = ['平静', '思考', '观察', '等待', '准备', '计划']

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        neutral_count = sum(1 for word in neutral_words if word in text)

        if positive_count > negative_count and positive_count > neutral_count:
            return "积极"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "消极"
        else:
            return "中性"

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python text_splitter.py <输入文件> [分割方法]")
        print("")
        print("分割方法:")
        print("  size    - 按大小分割 (默认)")
        print("  chapter - 按章节分割")
        print("")
        print("示例:")
        print("  python text_splitter.py novel.txt")
        print("  python text_splitter.py novel.txt chapter")
        return
    
    input_file = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "size"
    
    splitter = TextSplitter()
    splitter.split_novel(input_file, method)

if __name__ == "__main__":
    main()

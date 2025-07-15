#!/usr/bin/env python3
"""
SillyTavern V2 世界书格式转换器
将生成的世界书转换为SillyTavern V2兼容格式
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any

class WorldbookFormatter:
    """世界书格式转换器"""
    
    def __init__(self, input_dir: str = "worldbook"):
        self.input_dir = Path(input_dir)
        self.input_path = self.input_dir / "worldbook.json"
        self.output_path = self.input_dir / "worldbook_st_v2.json"
    
    def convert(self):
        """转换世界书格式"""
        print("="*60)
        print("[CONVERT] SillyTavern V2 世界书格式转换器 v1.5 (最终结构修复版)")
        print("="*60)

        if not self.input_path.exists():
            print(f"[ERROR] 错误: 找不到输入文件 '{self.input_path}'。")
            return

        try:
            print(f"[READ] 正在读取源文件: {self.input_path}")
            with open(self.input_path, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] 读取或解析JSON文件时发生错误: {e}")
            return

        # 检查数据结构
        if not isinstance(source_data, dict):
            print(f"[ERROR] 源文件格式错误: 期望字典，得到 {type(source_data)}")
            return

        # 提取所有章节的条目
        source_entries_list = []
        for chapter_name, chapter_data in source_data.items():
            if isinstance(chapter_data, dict) and 'entries' in chapter_data:
                entries = chapter_data['entries']
                if isinstance(entries, list):
                    source_entries_list.extend(entries)
                else:
                    print(f"[WARNING] 章节 '{chapter_name}' 的条目不是列表格式")

        if not source_entries_list:
            print("[ERROR] 没有找到有效的条目数据")
            return

        print(f"[INFO] 找到 {len(source_entries_list)} 个源条目")

        # 转换为SillyTavern V2格式
        final_entries_object = []
        
        for entry in source_entries_list:
            if not isinstance(entry, dict):
                continue
                
            # 创建SillyTavern V2条目
            st_entry = {
                "uid": str(uuid.uuid4()),
                "key": [entry.get('name', '未知')],
                "keysecondary": entry.get('aliases', []) if isinstance(entry.get('aliases'), list) else [],
                "comment": entry.get('category', ''),
                "content": entry.get('description', ''),
                "constant": False,
                "selective": True,
                "selectiveLogic": 0,
                "addMemo": False,
                "order": 100,
                "position": 0,
                "disable": False,
                "excludeRecursion": False,
                "probability": 100,
                "useProbability": True
            }
            
            final_entries_object.append(st_entry)

        # 创建最终的SillyTavern V2世界书结构
        final_worldbook = {
            "entries": final_entries_object,
            "name": "AI生成世界书",
            "description": "基于AI智能分析生成的高质量世界书",
            "scanDepth": 100,
            "tokenBudget": 500,
            "recursiveScanning": True,
            "extensions": {
                "world_info_depth": 4,
                "world_info_min_activations": 0,
                "world_info_min_activations_depth_max": 3,
                "world_info_max_recursion_depth": 5
            }
        }

        # 保存转换后的文件
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(final_worldbook, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 保存文件时发生错误: {e}")
            return

        print("\n" + "="*60)
        print(f"[SUCCESS] 转换成功！数据结构问题已修复。")
        print(f"总共处理了 {len(source_entries_list)} 个章节，生成了 {len(final_entries_object)} 个SillyTavern条目。")
        print(f"输出文件路径: {self.output_path}")
        print("这个版本应该能解决所有已知的加载问题了。")
        print("="*60)

def main():
    """主函数"""
    formatter = WorldbookFormatter()
    formatter.convert()

if __name__ == "__main__":
    main()
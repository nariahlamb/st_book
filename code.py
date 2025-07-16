#!/usr/bin/env python3
"""
SillyTavern V2 世界书格式转换器
================================
本脚本用于将 "st_book" 项目生成的、以“类别”为章节的深度世界书JSON文件，
转换为 SillyTavern V2 直接支持的标准格式。

V1.5 - [最终结构修复] 彻底重构输出格式，确保 "entries" 字段是一个以
       数字为键的对象，而不是数组，以完全匹配 SillyTavern 的UI解析逻辑。
"""

import json
from pathlib import Path
import re
from worldbook_parameter_optimizer import WorldbookParameterOptimizer

# --- 配置区 ---
INPUT_FILENAME = "worldbook.json"
OUTPUT_FILENAME = "worldbook_st_v2.json"
WORLDBOOK_DIR = "worldbook"

class WorldbookFormatter:
    """将自定义世界书格式转换为SillyTavern V2标准格式"""

    def __init__(self, input_dir: str):
        self.input_path = Path(input_dir) / INPUT_FILENAME
        self.output_path = Path(input_dir) / OUTPUT_FILENAME
        self.parameter_optimizer = WorldbookParameterOptimizer()

    def clean_text_for_json(self, text: str) -> str:
        """预处理文本，确保其对于JSON是安全的"""
        if not isinstance(text, str):
            text = str(text)
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    def convert(self):
        """执行转换流程"""
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

        source_entries_list = source_data.get("entries", [])
        
        if not source_entries_list:
            print("\n" + "!"*60)
            print("🛑 致命错误: 源文件 'worldbook.json' 中的 'entries' 数组为空！")
            print("   已中止转换。")
            print("!"*60)
            return

        # [V1.5 CRITICAL FIX] SillyTavern 的 "entries" 是一个对象，而不是列表！
        final_entries_object = {}
        print("🔄 开始转换条目...")
        
        entry_uid_counter = 0
        for entry in source_entries_list:
            primary_keys = entry.get("key", [])
            if not primary_keys or not isinstance(primary_keys, list):
                continue

            content = entry.get("content", "")
            if not content:
                continue
            
            cleaned_content = self.clean_text_for_json(content)

            title_keys = {self.clean_text_for_json(re.sub(r'\(.*?\)', '', k).strip()) for k in re.findall(r'#+\s*(.+)', cleaned_content)}
            bold_keys = {self.clean_text_for_json(re.sub(r'\(.*?\)', '', k).strip()) for k in re.findall(r'\*\*(.*?)\*\*', cleaned_content)}
            
            secondary_keys_set = title_keys.union(bold_keys)
            for pk in primary_keys:
                secondary_keys_set.discard(pk)
            
            final_primary_keys = sorted([k for k in primary_keys if k])
            final_secondary_keys = sorted([k for k in secondary_keys_set if k])
            
            if not final_primary_keys:
                continue
            
            # [V2.0 智能参数优化] 使用智能参数优化器
            optimized_params = self.parameter_optimizer.optimize_entry_parameters(
                entry=entry,
                entry_type=entry.get('type'),
                content=cleaned_content
            )

            # 构建完全符合示例的条目对象，使用优化后的参数
            new_entry_data = {
                "key": final_primary_keys,
                "keysecondary": optimized_params.get('keysecondary', final_secondary_keys),
                "comment": optimized_params.get('comment', self.clean_text_for_json(entry.get("comment", ""))),
                "content": cleaned_content,
                "constant": optimized_params.get('constant', False),
                "selective": optimized_params.get('selective', True),
                "addMemo": optimized_params.get('addMemo', False),
                "order": optimized_params.get('order', 100),
                "position": optimized_params.get('position', 0),
                "disable": optimized_params.get('disable', False),
                "excludeRecursion": optimized_params.get('excludeRecursion', False),
                "preventRecursion": optimized_params.get('preventRecursion', False),
                "probability": optimized_params.get('probability', 100),
                "useProbability": optimized_params.get('useProbability', True),
                "depth": optimized_params.get('depth', 4),
                # 添加其他在示例中看到的字段，并提供默认值
                "uid": entry_uid_counter,
                "displayIndex": entry_uid_counter,
                "extensions": {} # 可以暂时留空或填充默认值
            }
            
            # 使用计数器作为对象的键
            final_entries_object[str(entry_uid_counter)] = new_entry_data
            entry_uid_counter += 1
            print(f"  -> 已转换条目: {primary_keys[0]} (UID: {entry_uid_counter-1})")

        # [V1.5 CRITICAL FIX] 构建最终的世界书对象
        st_v2_worldbook = {
            "name": source_data.get("name", "自动转换的世界书"),
            "description": source_data.get("description", "由格式转换器自动生成"),
            "entries": final_entries_object # 这里现在是一个对象
        }
        
        try:
            print(f"\n💾 正在保存为最终兼容格式文件: {self.output_path}")
            json_string = json.dumps(st_v2_worldbook, ensure_ascii=False, indent=4) # indent=4更接近示例格式
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(json_string)
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
    formatter = WorldbookFormatter(WORLDBOOK_DIR)
    formatter.convert()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
角色筛选器 - 根据文件大小保留前N个最大的角色文件
"""

import json
import os
from pathlib import Path
from typing import List, Tuple
from project_config import get_config

class CharacterFilter:
    """根据文件大小筛选角色，保留内容最丰富的角色"""
    
    def __init__(self):
        self.config = get_config()
        self.input_dir = Path(self.config.get("output.roles_json_dir", "roles_json"))
        self.backup_dir = Path(self.config.get("output.roles_json_dir", "roles_json")) / "filtered_out"
        
        # 从配置读取保留数量，默认50个
        self.keep_count = int(self.config.get("character_filter.keep_count", 50))
        
    def get_character_files_by_size(self) -> List[Tuple[Path, int, int]]:
        """获取所有角色文件，按文件大小排序
        
        Returns:
            List[Tuple[Path, int, int]]: (文件路径, 文件大小, 角色数量)
        """
        if not self.input_dir.exists():
            print(f"[ERROR] 角色目录不存在: {self.input_dir}")
            return []
        
        character_files = []
        
        for json_file in self.input_dir.glob("*.json"):
            try:
                file_size = json_file.stat().st_size
                
                # 读取文件获取角色数量
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    char_count = 1 if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
                
                character_files.append((json_file, file_size, char_count))
                
            except Exception as e:
                print(f"[WARNING] 读取文件失败 {json_file.name}: {e}")
                continue
        
        # 按文件大小降序排序（大文件在前）
        character_files.sort(key=lambda x: x[1], reverse=True)
        
        return character_files
    
    def filter_characters(self, dry_run: bool = False) -> Tuple[int, int]:
        """筛选角色文件，保留前N个最大的文件
        
        Args:
            dry_run: 是否只是预览，不实际移动文件
            
        Returns:
            Tuple[int, int]: (保留的文件数, 移除的文件数)
        """
        character_files = self.get_character_files_by_size()
        
        if not character_files:
            print("[INFO] 没有找到角色文件")
            return 0, 0
        
        total_files = len(character_files)
        keep_files = character_files[:self.keep_count]
        remove_files = character_files[self.keep_count:]
        
        print(f"[STATS] 角色文件统计:")
        print(f"   总文件数: {total_files}")
        print(f"   保留文件数: {len(keep_files)}")
        print(f"   移除文件数: {len(remove_files)}")
        
        if dry_run:
            print("\n[PREVIEW] 预览模式 - 将要保留的文件:")
            for i, (file_path, file_size, char_count) in enumerate(keep_files[:10], 1):
                print(f"   {i:2d}. {file_path.name} ({file_size:,} bytes, {char_count} 角色)")
            
            if len(keep_files) > 10:
                print(f"   ... 还有 {len(keep_files) - 10} 个文件")
            
            if remove_files:
                print(f"\n[REMOVE] 将要移除的文件: {len(remove_files)} 个")
                for i, (file_path, file_size, char_count) in enumerate(remove_files[:5], 1):
                    print(f"   {i:2d}. {file_path.name} ({file_size:,} bytes, {char_count} 角色)")
                if len(remove_files) > 5:
                    print(f"   ... 还有 {len(remove_files) - 5} 个文件")
            
            return len(keep_files), len(remove_files)
        
        # 实际执行筛选
        if remove_files:
            # 创建备份目录
            self.backup_dir.mkdir(exist_ok=True)
            
            print(f"\n[MOVE] 移动 {len(remove_files)} 个小文件到备份目录...")
            moved_count = 0
            
            for file_path, file_size, char_count in remove_files:
                try:
                    backup_path = self.backup_dir / file_path.name
                    file_path.rename(backup_path)
                    moved_count += 1
                    
                    if moved_count <= 5:  # 只显示前5个
                        print(f"   [OK] {file_path.name} -> {backup_path.name}")
                    elif moved_count == 6:
                        print(f"   ... 继续移动剩余文件")
                        
                except Exception as e:
                    print(f"   [ERROR] 移动失败 {file_path.name}: {e}")
            
            print(f"[SUCCESS] 成功移动 {moved_count} 个文件到 {self.backup_dir}")
        
        print(f"\n[DONE] 筛选完成!")
        print(f"   保留了前 {len(keep_files)} 个最大的角色文件")
        print(f"   移除了 {len(remove_files)} 个较小的文件")
        
        return len(keep_files), len(remove_files)
    
    def show_statistics(self):
        """显示角色文件统计信息"""
        character_files = self.get_character_files_by_size()
        
        if not character_files:
            print("[INFO] 没有找到角色文件")
            return
        
        total_files = len(character_files)
        total_size = sum(size for _, size, _ in character_files)
        total_chars = sum(count for _, _, count in character_files)
        
        print(f"[STATS] 角色文件统计:")
        print(f"   总文件数: {total_files}")
        print(f"   总大小: {total_size:,} bytes ({total_size/1024:.1f} KB)")
        print(f"   总角色数: {total_chars}")
        
        if total_files > 0:
            avg_size = total_size / total_files
            avg_chars = total_chars / total_files
            print(f"   平均文件大小: {avg_size:.0f} bytes")
            print(f"   平均角色数: {avg_chars:.1f}")
        
        print(f"\n[TOP10] 前10个最大的文件:")
        for i, (file_path, file_size, char_count) in enumerate(character_files[:10], 1):
            print(f"   {i:2d}. {file_path.name:<30} {file_size:>8,} bytes  {char_count:>3} 角色")

def main():
    """主函数"""
    import sys
    
    filter_tool = CharacterFilter()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python character_filter.py stats     - 显示统计信息")
        print("  python character_filter.py preview   - 预览筛选结果")
        print("  python character_filter.py filter    - 执行筛选")
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        filter_tool.show_statistics()
    elif command == "preview":
        filter_tool.filter_characters(dry_run=True)
    elif command == "filter":
        filter_tool.filter_characters(dry_run=False)
    else:
        print(f"[ERROR] 未知命令: {command}")

if __name__ == "__main__":
    main()
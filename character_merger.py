#!/usr/bin/env python3
"""
角色合并器 V2.2 - 采用非贪婪匹配，彻底修复正则表达式错误
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import difflib
from opencc import OpenCC
from project_config import get_config

class CharacterMerger:
    """智能角色合并器 V2.2"""

    def __init__(self):
        self.config = get_config()
        self.input_dir = Path(self.config.get("output.character_responses_dir", "character_responses"))
        self.output_dir = Path(self.config.get("output.roles_json_dir", "roles_json"))
        self.output_dir.mkdir(exist_ok=True)
        
        self.cc = OpenCC('t2s.json')

        # 使用新的配置系统
        self.name_similarity_threshold = self.config.get("similarity.name_threshold", 0.85)
        self.content_similarity_threshold = self.config.get("similarity.content_threshold", 0.8)
        self.name_mappings = self.config.get("name_normalization.name_mappings", {})

    def normalize_name(self, name: str) -> str:
        """[V2.2 最终修复] 使用非贪婪匹配重构名称标准化函数"""
        name = self.cc.convert(name.strip().lower())
        
        if name in self.name_mappings:
            return self.name_mappings[name]
        
        prefixes = ["老", "小", "阿"]
        suffixes = ["队长", "先生", "小姐", "法师", "大人", "陛下"]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # [V2.2 核心修复] 使用更稳健的非贪婪匹配 (.*?)
        # 这个模式会匹配 "本名：" 等关键词之后，到第一个右括号之前的所有内容
        bracket_match = re.search(r'[（(](?:本名|真名|原名)[:：\s]*(.*?)[)）]', name)
        if bracket_match:
            # group(1) 捕获的是 (.*?) 的内容
            return self.cc.convert(bracket_match.group(1).strip().lower())
        
        # 如果没有匹配到 "本名" 等模式，再做一次通用的括号内容移除
        name = re.sub(r'[（(].*?[)）]', '', name).strip()
        
        return name

    def create_feature_set(self, entry: Dict[str, Any]) -> set:
        """为条目创建特征集，用于内容相似度比较"""
        features = set()
        # [健壮性优化] 安全地获取并合并文本
        desc_parts = [
            entry.get('features', ''),
            entry.get('personality', ''),
            entry.get('特徵', ''),
            entry.get('特征', ''),
            entry.get('性格', '')
        ]
        desc_text = " ".join(filter(None, desc_parts))
        keywords = re.split(r'[\s，；、,;]+', desc_text)
        features.update([self.cc.convert(kw.lower()) for kw in keywords if kw])
        return features

    def calculate_similarity(self, char1_data: Dict, char2_data: Dict) -> float:
        """计算两个角色实体的综合相似度"""
        name1 = char1_data['name']
        name2 = char2_data['name']
        
        norm_name1 = self.normalize_name(name1)
        norm_name2 = self.normalize_name(name2)

        name_sim = difflib.SequenceMatcher(None, norm_name1, norm_name2).ratio()
        
        if norm_name1 and norm_name2 and (norm_name1 in norm_name2 or norm_name2 in norm_name1):
            name_boost_threshold = float(self.config.get("similarity.name_boost_threshold", 0.9))
            name_sim = max(name_sim, name_boost_threshold)

        features1 = char1_data['feature_set']
        features2 = char2_data['feature_set']
        
        intersection = len(features1.intersection(features2))
        union = len(features1.union(features2))
        content_sim = intersection / union if union > 0 else 0.0

        if name_sim >= self.name_similarity_threshold:
            return name_sim
        
        combined_sim = (name_sim * 0.8) + (content_sim * 0.2)
        return combined_sim

    def _select_best_character_name(self, all_names: List[str]) -> str:
        """智能选择最佳的角色名称，避免选择关系描述性名称"""
        if not all_names:
            return "未知角色"

        # 过滤掉明显的关系描述性名称
        relationship_patterns = [
            "的父亲", "的母亲", "的儿子", "的女儿", "的妻子", "的丈夫",
            "的师父", "的师兄", "的师弟", "的师姐", "的师妹", "的徒弟",
            "的朋友", "的同伴", "的手下", "的属下", "的部下",
            "（假）", "（真）", "（幻觉）", "（现实）"
        ]

        # 分类名称
        clean_names = []  # 干净的名称（不含关系描述）
        descriptive_names = []  # 关系描述性名称

        for name in all_names:
            name = name.strip()
            if not name:
                continue

            is_descriptive = False
            for pattern in relationship_patterns:
                if pattern in name:
                    descriptive_names.append(name)
                    is_descriptive = True
                    break

            if not is_descriptive:
                clean_names.append(name)

        # 优先选择干净的名称
        if clean_names:
            # 在干净的名称中，选择最短的（通常是真正的角色名）
            return min(clean_names, key=len)

        # 如果只有关系描述性名称，选择最短的
        if descriptive_names:
            return min(descriptive_names, key=len)

        # 兜底：选择最短的名称
        return min(all_names, key=len)

    def merge_character_entries(self, entries: List[Dict]) -> Dict:
        """合并同一角色的多个条目"""
        if not entries:
            return {}

        all_names = [e.get('name') or e.get('名字') for e in entries if e.get('name') or e.get('名字')]
        if not all_names: return {}

        # 过滤掉None值并确保都是字符串
        valid_names = [str(name) for name in all_names if name]
        if not valid_names: return {}

        main_name = self._select_best_character_name(valid_names)
        
        aliases = set(self.cc.convert(str(name).lower()) for name in valid_names if name != main_name)
        aliases.discard(self.cc.convert(main_name.lower()))

        descriptions = []
        personalities = set()
        quotes = []
        motivations = []
        
        for entry in entries:
            desc = entry.get('features') or entry.get('特徵') or entry.get('特征')
            if desc and desc not in descriptions:
                descriptions.append(str(desc))

            pers = entry.get('personality') or entry.get('性格')
            if pers:
                pers_list = re.split(r'[，；、,;]+', str(pers))
                personalities.update([p.strip() for p in pers_list if p.strip()])

            quote = entry.get('quote') or entry.get('说话习惯') or entry.get('說話習慣')
            if quote and quote not in quotes:
                quotes.append(str(quote))
            
            motive = entry.get('motivation')
            if motive and motive not in motivations:
                motivations.append(str(motive))

        merged = {
            "name": main_name,
            "description": '\n'.join(descriptions),
            "personality": '\n'.join(sorted(list(personalities))),
            "scenario": f"别名: {', '.join(sorted(list(aliases)))}\n动机: {' 或 '.join(motivations) if motivations else '未知'}",
            "first_message": '\n'.join(quotes),
            "mes_example": "",
            "creator": self.config.get("character_card.creator", "st_book_v2"),
            "character_version": self.config.get("character_card.character_version", "2.0"),
            "tags": list(personalities)[:self.config.get("character_card.max_tags", 5)],
            "metadata": {
                "merged_from_names": sorted(list(set(valid_names))),
                "entry_count": len(entries),
                "source_files": sorted(list(set(e.get('source_file', '') for e in entries if e.get('source_file'))))
            }
        }
        return merged

    def find_character_clusters(self, all_char_data: List[Dict]) -> List[List[Dict]]:
        """使用并查集算法进行角色聚类"""
        parent = list(range(len(all_char_data)))
        
        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_j] = root_i

        print("\n[CLUSTER] 开始多维度相似度计算与聚类...")
        for i in range(len(all_char_data)):
            for j in range(i + 1, len(all_char_data)):
                char1 = all_char_data[i]
                char2 = all_char_data[j]
                
                similarity = self.calculate_similarity(char1, char2)
                
                if similarity >= self.name_similarity_threshold:
                    union(i, j)

        clusters = defaultdict(list)
        for i in range(len(all_char_data)):
            root = find(i)
            clusters[root].append(all_char_data[i])
        
        print(f"聚类完成，找到 {len(clusters)} 个独立角色实体。")
        return list(clusters.values())

    def merge_all_characters(self):
        """主合并流程"""
        print("="*60)
        print("角色合并器 V2.2 - 修复版")
        print("="*60)
        
        if not self.input_dir.exists():
            print(f"[ERROR] 错误: 找不到角色数据目录 {self.input_dir}")
            return

        all_char_data = []
        char_files = list(self.input_dir.glob("*.json"))
        print(f"[LOAD] 从 {len(char_files)} 个文件中加载角色条目...")
        
        for char_file in char_files:
            try:
                with open(char_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                
                if not isinstance(entries, list): continue
                
                for entry in entries:
                    name = entry.get('name') or entry.get('名字')
                    if name and isinstance(name, str) and name.strip():
                        all_char_data.append({
                            "name": name.strip(),
                            "feature_set": self.create_feature_set(entry),
                            "original_entry": entry,
                            "source_file": char_file.name
                        })
            except Exception as e:
                print(f"[WARNING] 加载文件失败 {char_file.name}: {e}")

        print(f"[SUCCESS] 加载了 {len(all_char_data)} 个角色条目。")

        clusters = self.find_character_clusters(all_char_data)

        print("\n[MERGE] 开始合并每个角色集群的数据...")
        merged_characters = {}
        for cluster in clusters:
            original_entries = [data['original_entry'] for data in cluster]
            merged_char_data = self.merge_character_entries(original_entries)
            
            if merged_char_data and merged_char_data.get("name"):
                final_name = merged_char_data["name"]
                merged_characters[final_name] = merged_char_data
                print(f"  合并了 {len(cluster)} 个条目到角色: {final_name}")

        self.save_merged_characters(merged_characters)
        
        print(f"\n{'='*60}")
        print(f"[DONE] 角色合并完成！")
        print(f"原始条目数: {len(all_char_data)}")
        print(f"合并后独立角色数: {len(merged_characters)}")
        print(f"[SAVE] 保存位置: {self.output_dir}")
        print("="*60)
    
    def save_merged_characters(self, characters: Dict[str, Dict]):
        """保存合并后的角色信息"""
        print(f"\n[SAVE] 正在保存 {len(characters)} 个角色卡...")
        for old_file in self.output_dir.glob("*.json"):
            old_file.unlink()

        for name, char_data in characters.items():
            safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
            output_file = self.output_dir / f"{safe_name}.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(char_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERROR] 保存角色失败 {name}: {e}")

def main():
    """主函数"""
    merger = CharacterMerger()
    merger.merge_all_characters()

if __name__ == "__main__":
    main()
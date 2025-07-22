#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
世界书分类器 (Worldbook Classifier)
负责将提取的原始规则和事件数据进行分类、标记和预处理
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

from project_config import get_config


class WorldbookClassifier:
    """世界书数据分类器"""
    
    def __init__(self):
        """初始化分类器"""
        self.config = get_config()
        self.input_dir = Path(self.config.get("output.wb_responses_dir", "wb_responses"))
        self.output_dir = self.input_dir / "classified"
        self.output_dir.mkdir(exist_ok=True)
        
        # 规则类型映射
        self.rule_type_keywords = {
            "历史背景": ["历史", "背景", "起源", "过去", "古代", "文明", "末日", "灾变"],
            "社会规则": ["社会", "组织", "势力", "协会", "签证", "试炼", "秩序"],
            "神明设定": ["神", "神明", "神祇", "最高神", "女娲", "母神", "枭西厄斯"],
            "地理背景": ["地理", "世界", "维度", "空间", "十二界", "副本", "传送"],
            "魔法体系": ["魔法", "意识力", "能力", "进化", "卡牌", "概念"],
            "物理法则": ["物理", "法则", "规则", "现实", "时空", "因果"],
            "修炼体系": ["修炼", "进化者", "潜力值", "伙伴", "成长"],
            "种族设定": ["种族", "人类", "堕落种", "进化者", "生物", "衍生物"],
            "技术水平": ["技术", "科技", "星舰", "AI", "莎莱斯", "副本构建"],
            "经济体系": ["经济", "货币", "晶石", "红晶", "交易", "eBay"],
            "生物设定": ["生物", "怪物", "衍生物", "副本生物", "长青虫"]
        }
        
        # 事件类型映射
        self.event_type_keywords = {
            "能力觉醒": ["觉醒", "能力", "获得", "激活"],
            "修炼突破": ["修炼", "突破", "提升", "成长"],
            "关系建立": ["关系", "结盟", "合作", "友谊"],
            "战斗冲突": ["战斗", "冲突", "对抗", "攻击"],
            "探索发现": ["探索", "发现", "调查", "寻找"],
            "危机事件": ["危机", "威胁", "危险", "灾难"],
            "重要决策": ["决策", "选择", "决定", "抉择"]
        }
        
        print(f"📂 分类器初始化完成，输出目录: {self.output_dir}")
    
    def classify_all(self) -> bool:
        """执行完整的分类流程"""
        try:
            print("🔄 开始执行世界书数据分类...")
            
            # 1. 分类规则
            print("📋 分类规则数据...")
            classified_rules = self.classify_rules()
            
            # 2. 分类事件并提取实体
            print("📅 分类事件数据...")
            classified_events, entities = self.classify_events()
            
            # 3. 生成统计报告
            self._generate_classification_report(classified_rules, classified_events, entities)
            
            print("✅ 世界书数据分类完成")
            return True
            
        except Exception as e:
            print(f"❌ 世界书数据分类失败: {e}")
            return False
    
    def classify_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """分类规则数据"""
        rules = self._load_rules()
        classified_rules = defaultdict(list)
        
        print(f"📊 开始分类 {len(rules)} 个规则...")
        
        for rule in rules:
            rule_type = self._detect_rule_type(rule)
            
            # 添加分类标签
            rule["type"] = rule_type
            rule["layer"] = "rules_layer"
            rule["suggested_order"] = self._calculate_rule_order(rule_type)
            rule["comment_prefix"] = "【世界规则】"
            
            classified_rules[rule_type].append(rule)
        
        # 保存分类结果
        self._save_classified_data("classified_rules.json", dict(classified_rules))
        
        print(f"✅ 规则分类完成，共 {len(classified_rules)} 种类型")
        return dict(classified_rules)
    
    def classify_events(self) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
        """分类事件数据并提取实体"""
        events = self._load_events()
        classified_events = defaultdict(list)
        entities = {}
        
        print(f"📊 开始分类 {len(events)} 个事件...")
        
        for event in events:
            event_type = event.get("event_type", "未分类事件")
            
            # 添加分类标签
            event["layer"] = "events_layer"
            event["suggested_order"] = self._calculate_event_order(event)
            event["comment_prefix"] = "【事件】"
            
            classified_events[event_type].append(event)
            
            # 提取实体
            self._extract_entities_from_event(event, entities)
        
        # 为实体添加标签
        for entity_name, entity_data in entities.items():
            entity_data["layer"] = "entity_layer"
            entity_data["suggested_order"] = self._calculate_entity_order(entity_data)
            entity_data["comment_prefix"] = "【核心实体】"
        
        # 保存分类结果
        self._save_classified_data("classified_events.json", dict(classified_events))
        self._save_classified_data("classified_entities.json", entities)
        
        print(f"✅ 事件分类完成，共 {len(classified_events)} 种类型")
        print(f"✅ 实体提取完成，共 {len(entities)} 个实体")
        
        return dict(classified_events), entities
    
    def _detect_rule_type(self, rule: Dict[str, Any]) -> str:
        """智能检测规则类型"""
        # 1. 优先使用原始数据中的rule_type字段
        if "rule_type" in rule and rule["rule_type"]:
            original_type = rule["rule_type"]
            # 映射原始类型到我们的分类体系
            type_mapping = {
                "魔法体系": "魔法体系",
                "修炼体系": "修炼体系",
                "社会规则": "社会规则",
                "历史背景": "历史背景",
                "地理背景": "地理背景",
                "神明设定": "神明设定",
                "物理法则": "物理法则",
                "种族设定": "种族设定",
                "技术水平": "技术水平",
                "经济体系": "经济体系",
                "生物设定": "生物设定"
            }
            if original_type in type_mapping:
                return type_mapping[original_type]

        # 2. 如果没有rule_type字段，则基于内容进行语义分析
        # 检查多个可能的描述字段
        rule_text = ""
        for field in ["description", "rule_description", "rule_summary"]:
            if field in rule and rule[field]:
                rule_text += rule[field].lower() + " "

        if not rule_text.strip():
            return "其他规则"

        # 3. 使用增强的关键词匹配和语义理解
        type_scores = {}
        for rule_type, keywords in self.rule_type_keywords.items():
            score = 0
            # 基础关键词匹配
            for keyword in keywords:
                if keyword in rule_text:
                    score += 1

            # 语义相关性加权
            if rule_type == "魔法体系" and any(word in rule_text for word in ["意识力", "能力", "力量", "魔法", "超能力", "异能"]):
                score += 2
            elif rule_type == "修炼体系" and any(word in rule_text for word in ["进化", "修炼", "提升", "成长", "突破"]):
                score += 2
            elif rule_type == "社会规则" and any(word in rule_text for word in ["组织", "势力", "社会", "制度", "规则"]):
                score += 2
            elif rule_type == "历史背景" and any(word in rule_text for word in ["历史", "过去", "起源", "背景", "文明"]):
                score += 2
            elif rule_type == "地理背景" and any(word in rule_text for word in ["地理", "世界", "地点", "空间", "维度"]):
                score += 2
            elif rule_type == "神明设定" and any(word in rule_text for word in ["神", "神明", "神祇", "女娲", "最高神"]):
                score += 2
            elif rule_type == "物理法则" and any(word in rule_text for word in ["物理", "法则", "规律", "现实", "时空"]):
                score += 2
            elif rule_type == "经济体系" and any(word in rule_text for word in ["经济", "货币", "交易", "晶石", "红晶"]):
                score += 2
            elif rule_type == "生物设定" and any(word in rule_text for word in ["生物", "怪物", "衍生物", "细胞", "病毒"]):
                score += 2

            if score > 0:
                type_scores[rule_type] = score

        # 返回得分最高的类型，如果没有匹配则返回"其他规则"
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        else:
            return "其他规则"
    
    def _calculate_rule_order(self, rule_type: str) -> int:
        """计算规则的建议优先级"""
        # 规则层优先级映射 (0-20)
        priority_map = {
            "历史背景": 0,
            "物理法则": 1,
            "魔法体系": 2,
            "社会规则": 3,
            "地理背景": 4,
            "神明设定": 5,
            "修炼体系": 6,
            "种族设定": 7,
            "技术水平": 8,
            "经济体系": 9,
            "生物设定": 10,
            "其他规则": 15
        }
        return priority_map.get(rule_type, 15)
    
    def _calculate_event_order(self, event: Dict[str, Any]) -> int:
        """计算事件的建议优先级"""
        # 基础优先级 (60-120)
        base_order = 60
        significance = event.get("significance", 5)
        
        # 重要性越高，优先级越高（order值越小）
        return base_order + (10 - significance) * 5
    
    def _calculate_entity_order(self, entity: Dict[str, Any]) -> int:
        """计算实体的建议优先级"""
        # 基础优先级 (30-50)
        base_order = 30
        event_count = len(entity.get("events", []))
        
        # 参与事件越多，优先级越高
        return base_order + max(0, 20 - event_count)
    
    def _extract_entities_from_event(self, event: Dict[str, Any], entities: Dict[str, Dict[str, Any]]):
        """从事件中提取实体信息"""
        participants = event.get("participants", {})
        
        # 处理主要参与者
        for participant in participants.get("primary", []):
            if participant and participant.strip():
                if participant not in entities:
                    entities[participant] = {
                        "name": participant,
                        "type": "character",
                        "events": [],
                        "total_significance": 0,
                        "event_count": 0,
                        "locations": [],
                        "items": []
                    }
                
                entities[participant]["events"].append(event)
                entities[participant]["total_significance"] += event.get("significance", 0)
                entities[participant]["event_count"] += 1
                
                # 添加相关地点和物品
                location = event.get("location")
                if location and location != "未知" and location not in entities[participant]["locations"]:
                    entities[participant]["locations"].append(location)

                for item in event.get("key_items", []):
                    if item and item not in entities[participant]["items"]:
                        entities[participant]["items"].append(item)
        
        # 处理次要参与者
        for participant in participants.get("secondary", []):
            if participant and participant.strip():
                if participant not in entities:
                    entities[participant] = {
                        "name": participant,
                        "type": "character",
                        "events": [],
                        "total_significance": 0,
                        "event_count": 0,
                        "locations": [],
                        "items": []
                    }
                
                entities[participant]["events"].append(event)
                entities[participant]["total_significance"] += event.get("significance", 0) * 0.5  # 次要参与者权重减半
                entities[participant]["event_count"] += 1
        
        # 计算平均重要性
        for entity_data in entities.values():
            if entity_data["event_count"] > 0:
                entity_data["average_significance"] = entity_data["total_significance"] / entity_data["event_count"]
            else:
                entity_data["average_significance"] = 0

    def _load_rules(self) -> List[Dict[str, Any]]:
        """加载原始规则数据"""
        rules = []
        rules_dir = self.input_dir / "rules"

        if not rules_dir.exists():
            print(f"⚠️ 规则目录不存在: {rules_dir}")
            return rules

        # 加载mapping.json获取chunk顺序
        mapping_file = Path(self.config.get("output.chunk_dir", "chunks")) / "mapping.json"
        chunk_order = {}

        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                chunk_order = {chunk['id']: chunk.get('order', 0) for chunk in mapping.get('chunks', [])}
            except Exception as e:
                print(f"⚠️ 加载mapping文件失败: {e}")

        # 按文件名排序加载规则文件
        rule_files = sorted(rules_dir.glob("chunk_*.json"))

        for file in rule_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    chunk_rules = json.load(f)

                # 为每个规则添加元数据
                chunk_id = file.stem
                for rule in chunk_rules:
                    if isinstance(rule, dict):
                        rule['source_chunk'] = chunk_id
                        rule['chunk_order'] = chunk_order.get(chunk_id, 0)
                        rules.append(rule)

            except Exception as e:
                print(f"⚠️ 加载规则文件 {file.name} 失败: {e}")
                continue

        print(f"📊 成功加载 {len(rules)} 个规则")
        return rules

    def _load_events(self) -> List[Dict[str, Any]]:
        """加载原始事件数据"""
        events = []
        events_dir = self.input_dir / "events"

        if not events_dir.exists():
            print(f"⚠️ 事件目录不存在: {events_dir}")
            return events

        # 加载mapping.json获取chunk顺序
        mapping_file = Path(self.config.get("output.chunk_dir", "chunks")) / "mapping.json"
        chunk_order = {}

        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                chunk_order = {chunk['id']: chunk.get('order', 0) for chunk in mapping.get('chunks', [])}
            except Exception as e:
                print(f"⚠️ 加载mapping文件失败: {e}")

        # 按文件名排序加载事件文件
        event_files = sorted(events_dir.glob("chunk_*.json"))

        for file in event_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    chunk_events = json.load(f)

                # 为每个事件添加元数据
                chunk_id = file.stem
                for event in chunk_events:
                    if isinstance(event, dict):
                        event['source_chunk'] = chunk_id
                        event['chunk_order'] = chunk_order.get(chunk_id, 0)
                        events.append(event)

            except Exception as e:
                print(f"⚠️ 加载事件文件 {file.name} 失败: {e}")
                continue

        print(f"📊 成功加载 {len(events)} 个事件")
        return events

    def _save_classified_data(self, filename: str, data: Any):
        """保存分类后的数据"""
        output_file = self.output_dir / filename
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存分类数据: {output_file}")
        except Exception as e:
            print(f"❌ 保存分类数据失败 {filename}: {e}")

    def _generate_classification_report(self, classified_rules: Dict, classified_events: Dict, entities: Dict):
        """生成分类统计报告"""
        report = {
            "classification_summary": {
                "rules": {
                    "total_count": sum(len(rules) for rules in classified_rules.values()),
                    "types_count": len(classified_rules),
                    "types": {rule_type: len(rules) for rule_type, rules in classified_rules.items()}
                },
                "events": {
                    "total_count": sum(len(events) for events in classified_events.values()),
                    "types_count": len(classified_events),
                    "types": {event_type: len(events) for event_type, events in classified_events.items()}
                },
                "entities": {
                    "total_count": len(entities),
                    "top_entities": sorted(
                        [(name, data["event_count"]) for name, data in entities.items()],
                        key=lambda x: x[1], reverse=True
                    )[:10]
                }
            },
            "layer_distribution": {
                "rules_layer": sum(len(rules) for rules in classified_rules.values()),
                "events_layer": sum(len(events) for events in classified_events.values()),
                "entity_layer": len(entities),
                "timeline_layer": 1  # 时间线层固定为1个条目
            }
        }

        self._save_classified_data("classification_report.json", report)

        # 打印统计信息
        print("\n" + "="*60)
        print("📊 分类统计报告")
        print("="*60)
        print(f"📋 规则层: {report['layer_distribution']['rules_layer']} 个条目，{report['classification_summary']['rules']['types_count']} 种类型")
        print(f"📅 事件层: {report['layer_distribution']['events_layer']} 个条目，{report['classification_summary']['events']['types_count']} 种类型")
        print(f"👥 实体层: {report['layer_distribution']['entity_layer']} 个条目")
        print(f"⏰ 时间线层: {report['layer_distribution']['timeline_layer']} 个条目")
        print("="*60)


if __name__ == "__main__":
    classifier = WorldbookClassifier()
    classifier.classify_all()

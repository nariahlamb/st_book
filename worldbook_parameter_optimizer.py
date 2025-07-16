#!/usr/bin/env python3
"""
SillyTavern世界书智能参数自动化赋值系统
===========================================
基于规则引擎、启发式算法和LLM判断的自动化赋值策略，
为每个世界书条目智能配置SillyTavern的行为控制参数。

功能特性：
- 三层参数分类体系：内容驱动型、行为控制型、元数据静态型
- 基于条目类型、内容长度、重要性等维度的动态参数配置
- 中文网文特殊元素优化（修炼体系、势力关系、别名等）
- 与现有project_config.py配置管理系统完全兼容
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from project_config import get_config


class WorldbookParameterOptimizer:
    """世界书参数智能优化器"""
    
    def __init__(self):
        """初始化优化器"""
        self.config = get_config()
        self.automation_config = self.config.get('worldbook_automation', {})
        self.enabled = self.automation_config.get('enable', True)
        
        if not self.enabled:
            print("⚠️ 世界书参数自动化已禁用，将使用默认参数")
    
    def optimize_entry_parameters(self, entry: Dict[str, Any], entry_type: str = None,
                                 content: str = None) -> Dict[str, Any]:
        """
        为单个世界书条目优化参数

        Args:
            entry: 原始世界书条目
            entry_type: 条目类型（如：主角、地点、组织等）
            content: 条目内容文本

        Returns:
            优化后的参数字典
        """
        if not self.enabled:
            return self._get_default_parameters()

        # 检查是否为事件驱动模式
        event_mode = self.config.get('event_driven_architecture.enable', True)

        if event_mode and 'significance' in entry:
            # 事件驱动模式：基于significance评分优化
            return self._optimize_event_parameters(entry, entry_type, content)
        else:
            # 传统模式：基于类型和内容优化
            return self._optimize_traditional_parameters(entry, entry_type, content)

    def _optimize_event_parameters(self, entry: Dict[str, Any], entry_type: str = None,
                                  content: str = None) -> Dict[str, Any]:
        """基于事件重要性评分优化参数"""
        significance = entry.get('significance', 5)
        event_type = entry.get('event_type', '未分类')

        # 初始化参数
        params = self._get_default_parameters()

        # 1. 根据重要性设置Order（数值越小优先级越高）
        # significance 10 -> order 10, significance 1 -> order 100
        params['order'] = 110 - (significance * 10)

        # 2. 根据重要性设置Constant（常驻内存）
        constant_threshold = self.automation_config.get('constant_significance_threshold', 9)
        if significance >= constant_threshold:
            params['constant'] = True
            params['selective'] = False  # 最重要的事件不需要选择性注入
        else:
            params['constant'] = False
            params['selective'] = True

        # 3. 根据重要性设置Depth（影响深度）
        # 越重要的事件，影响应该越深远
        base_depth = 2
        params['depth'] = base_depth + (significance // 2)  # 2-7的范围

        # 4. 根据重要性设置Probability（触发概率）
        # 重要事件应该有更高的触发概率
        base_probability = 60
        params['probability'] = min(100, base_probability + (significance * 4))

        # 5. 特殊事件类型优化
        params = self._apply_event_type_optimization(params, event_type, significance)

        # 6. 生成次要关键词（从事件参与者和地点提取）
        params['keysecondary'] = self._generate_event_secondary_keys(entry)

        # 7. 生成comment总结
        params['comment'] = self._generate_event_comment(entry)

        # 8. 应用中文网文特殊优化
        content = content or entry.get('content', '')
        params = self._apply_chinese_webnovel_optimization(params, content, event_type)

        return params

    def _optimize_traditional_parameters(self, entry: Dict[str, Any], entry_type: str = None,
                                       content: str = None) -> Dict[str, Any]:
        """传统模式：基于类型和内容优化参数"""
        # 提取基础信息
        content = content or entry.get('content', '')
        entry_type = entry_type or self._detect_entry_type(entry, content)

        # 初始化参数
        params = self._get_base_parameters(entry_type)

        # 应用内容长度调整
        params = self._apply_content_length_adjustments(params, content)

        # 应用关键词密度分析
        params = self._apply_keyword_density_analysis(params, content, entry)

        # 应用中文网文特殊优化
        params = self._apply_chinese_webnovel_optimization(params, content, entry_type)

        # 生成次要关键词
        params['keysecondary'] = self._generate_secondary_keys(content, entry.get('key', []))

        # 生成comment总结
        params['comment'] = self._generate_comment(entry, entry_type)

        return params

    def _apply_event_type_optimization(self, params: Dict[str, Any], event_type: str,
                                     significance: int) -> Dict[str, Any]:
        """根据事件类型进行特殊优化"""
        # 战斗事件和修炼突破通常更重要
        high_priority_types = ['战斗事件', '修炼突破', '阴谋揭露', '势力变动']
        if event_type in high_priority_types:
            params['order'] = max(10, params['order'] - 10)  # 提升优先级
            params['probability'] = min(100, params['probability'] + 10)

        # 背景揭示类事件可以降低优先级
        low_priority_types = ['背景揭示', '地点探索']
        if event_type in low_priority_types:
            params['order'] = min(120, params['order'] + 10)  # 降低优先级
            params['selective'] = True  # 启用选择性注入

        return params

    def _generate_event_secondary_keys(self, entry: Dict[str, Any]) -> List[str]:
        """从事件信息生成次要关键词"""
        secondary_keys = set()

        # 从参与者提取
        participants = entry.get('participants', {})
        for participant_list in participants.values():
            if isinstance(participant_list, list):
                secondary_keys.update(participant_list)

        # 从地点提取
        location = entry.get('location', '')
        if location:
            secondary_keys.add(location)

        # 从重要物品提取
        key_items = entry.get('key_items', [])
        secondary_keys.update(key_items)

        # 从事件类型提取
        event_type = entry.get('event_type', '')
        if event_type:
            secondary_keys.add(event_type)

        # 过滤空值并转换为列表
        return sorted(list({k.strip() for k in secondary_keys if k and k.strip()}))

    def _generate_event_comment(self, entry: Dict[str, Any]) -> str:
        """生成事件条目的注释"""
        event_summary = entry.get('event_summary', '未知事件')
        event_type = entry.get('event_type', '事件')
        significance = entry.get('significance', 5)

        return f"【{event_type}】{event_summary} (重要性:{significance})"

    def _get_default_parameters(self) -> Dict[str, Any]:
        """获取默认参数配置"""
        default_config = self.config.get('sillytavern_worldbook.default_entry', {})
        return {
            'order': default_config.get('order', 100),
            'constant': False,
            'selective': True,
            'addMemo': False,
            'depth': default_config.get('depth', 4),
            'probability': default_config.get('probability', 100),
            'position': default_config.get('position', 0),
            'disable': False,
            'excludeRecursion': False,
            'preventRecursion': False,
            'useProbability': True,
            'keysecondary': [],
            'comment': ''
        }
    
    def _get_base_parameters(self, entry_type: str) -> Dict[str, Any]:
        """根据条目类型获取基础参数"""
        params = self._get_default_parameters()
        
        # 设置order权重
        order_weights = self.automation_config.get('order_weights', {})
        params['order'] = order_weights.get(entry_type, order_weights.get('默认', 100))
        
        # 设置constant字段
        constant_types = self.automation_config.get('constant_types', [])
        params['constant'] = entry_type in constant_types
        
        # 设置depth字段
        depth_mapping = self.automation_config.get('depth_mapping', {})
        params['depth'] = depth_mapping.get(entry_type, depth_mapping.get('默认', 4))
        
        # 设置probability字段
        probability_mapping = self.automation_config.get('probability_mapping', {})
        params['probability'] = probability_mapping.get(entry_type, probability_mapping.get('默认', 80))
        
        return params
    
    def _detect_entry_type(self, entry: Dict[str, Any], content: str) -> str:
        """智能检测条目类型"""
        # 优先使用已有的type字段
        if 'type' in entry:
            return entry['type']
        
        # 基于关键词检测
        content_lower = content.lower()
        
        # 检测修炼体系
        cultivation_keywords = self.automation_config.get('chinese_webnovel_optimization.cultivation_keywords', [])
        if any(keyword in content for keyword in cultivation_keywords):
            return '修炼体系'
        
        # 检测组织
        if any(keyword in content for keyword in ['组织', '门派', '宗门', '公会', '帮派']):
            return '组织'
        
        # 检测地点
        if any(keyword in content for keyword in ['城市', '山脉', '森林', '王国', '大陆']):
            return '地点'
        
        # 检测角色
        if any(keyword in content for keyword in ['主角', '男主', '女主', '主人公']):
            return '主角'
        
        return '默认'
    
    def _apply_content_length_adjustments(self, params: Dict[str, Any], content: str) -> Dict[str, Any]:
        """基于内容长度应用动态调整"""
        content_length = len(content)
        adjustments = self.automation_config.get('content_length_adjustments', {})
        
        short_threshold = adjustments.get('short_content_threshold', 200)
        long_threshold = adjustments.get('long_content_threshold', 1000)
        
        # 短内容优化
        if content_length < short_threshold:
            boost = adjustments.get('short_content_probability_boost', 10)
            params['probability'] = min(100, params['probability'] + boost)
            params['selective'] = False  # 短内容不需要选择性注入
        
        # 长内容优化
        elif content_length > long_threshold:
            depth_increase = adjustments.get('long_content_depth_increase', 1)
            params['depth'] = params['depth'] + depth_increase
            params['selective'] = True  # 长内容启用选择性注入
        
        # 选择性注入阈值检查
        selective_threshold = self.automation_config.get('selective_threshold', 800)
        if content_length > selective_threshold:
            params['selective'] = True
        
        return params
    
    def _apply_keyword_density_analysis(self, params: Dict[str, Any], content: str, 
                                      entry: Dict[str, Any]) -> Dict[str, Any]:
        """应用关键词密度分析"""
        if not self.automation_config.get('keyword_density_analysis.enable', True):
            return params
        
        # 计算关键词密度
        primary_keys = entry.get('key', [])
        if not primary_keys:
            return params
        
        total_words = len(content.split())
        if total_words == 0:
            return params
        
        keyword_count = sum(content.lower().count(key.lower()) for key in primary_keys)
        density = keyword_count / total_words
        
        # 高密度条目优先级提升
        high_density_threshold = self.automation_config.get('keyword_density_analysis.high_density_threshold', 0.05)
        if density > high_density_threshold:
            boost = self.automation_config.get('keyword_density_analysis.high_density_order_boost', -10)
            params['order'] = params['order'] + boost
        
        return params
    
    def _apply_chinese_webnovel_optimization(self, params: Dict[str, Any], content: str, 
                                           entry_type: str) -> Dict[str, Any]:
        """应用中文网文特殊优化"""
        if not self.automation_config.get('chinese_webnovel_optimization.enable', True):
            return params
        
        # 修炼体系特殊处理
        cultivation_keywords = self.automation_config.get('chinese_webnovel_optimization.cultivation_keywords', [])
        if any(keyword in content for keyword in cultivation_keywords):
            boost = self.automation_config.get('chinese_webnovel_optimization.power_system_boost', -20)
            params['order'] = params['order'] + boost
            params['constant'] = True  # 修炼体系常驻内存
        
        return params
    
    def _generate_secondary_keys(self, content: str, primary_keys: List[str]) -> List[str]:
        """生成次要关键词"""
        secondary_keys = set()
        
        # 提取标题关键词
        title_pattern = r'#+\s*(.+)'
        titles = re.findall(title_pattern, content)
        for title in titles:
            clean_title = re.sub(r'\(.*?\)', '', title).strip()
            if clean_title and clean_title not in primary_keys:
                secondary_keys.add(clean_title)
        
        # 提取粗体关键词
        bold_pattern = r'\*\*(.*?)\*\*'
        bold_texts = re.findall(bold_pattern, content)
        for bold_text in bold_texts:
            clean_bold = re.sub(r'\(.*?\)', '', bold_text).strip()
            if clean_bold and clean_bold not in primary_keys:
                secondary_keys.add(clean_bold)
        
        return sorted(list(secondary_keys))
    
    def _generate_comment(self, entry: Dict[str, Any], entry_type: str) -> str:
        """生成条目注释"""
        name = entry.get('name', '')
        if name:
            return f"【{entry_type}】{name}"
        
        primary_keys = entry.get('key', [])
        if primary_keys:
            return f"【{entry_type}】{primary_keys[0]}"
        
        return f"【{entry_type}】未命名条目"
    
    def _check_addmemo_content(self, content: str) -> bool:
        """检查内容是否包含指令性关键词"""
        addmemo_keywords = self.automation_config.get('addmemo_keywords', [])
        return any(keyword in content for keyword in addmemo_keywords)

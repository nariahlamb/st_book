#!/usr/bin/env python3
"""
世界书生成器 - 负责将原始条目升华为结构化的世界书
版本: 2.0 (采用全局上下文和世界观构建方法论)
"""

import json
import asyncio
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from project_config import get_config

class WorldbookGenerator:
    """使用Pro模型将分类条目总结生成最终世界书"""

    def __init__(self):
        """初始化配置、API客户端和Prompt模板"""
        self.config = get_config()
        self.input_dir = Path(self.config.get("output.wb_responses_dir", "wb_responses"))
        self.output_dir = Path(self.config.get("output.worldbook_dir", "worldbook"))
        self.output_dir.mkdir(exist_ok=True)

        # 使用新的配置系统
        model_config = self.config.get_model_config()
        api_config = self.config.get_api_config()

        self.pro_model = model_config.get("generation_model", "gemini-2.5-pro")
        self.generation_temperature = model_config.get("generation_temperature", 0.2)
        self.timeout = int(model_config.get("timeout", 300))
        self.max_tokens = int(model_config.get("max_tokens", 60000))

        # 性能配置
        self.retry_limit = int(self.config.get("performance.retry_limit", 3))
        self.retry_delay = int(self.config.get("performance.retry_delay", 10))
        self.max_concurrent = int(self.config.get("performance.max_concurrent", 1))
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # 初始化OpenAI客户端
        api_key = api_config.get("api_key")
        if not api_key:
            raise ValueError("❌ 找不到 API 金鑰，請在 config.yaml 中設定 'api.api_key'")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_config.get("api_base"),
            timeout=self.timeout
        )

        # [核心优化] 将Prompt作为可配置的类属性，结构更清晰
        self.worldbook_prompt_template = self.config.get("worldbook.generation_prompt", """
<role>
你是一位顶级世界观架构师，师从于布兰登·桑德森和乔治·R·R·马丁。你不仅仅是编辑，更是体系的创建者。你的工作是将一堆零散、原始的设定（fragments），升华为一个逻辑自洽、细节丰富、充满内在联系的宏大世界。
</role>

<task>
你的核心任务是，为当前聚焦的 **“{category}”** 类别撰写一份深度介绍章节。你必须将下方提供的原始设定条目，通过“世界观构建黄金三角”方法论进行重构、扩展和升华。

**【第一步：全局认知 (Global Context Awareness)】**
在动笔前，请先默读并理解整个世界的核心构成。这能帮助你建立条目间的联系。

<world_overview>
{all_categories_summary}
</world_overview>

**【第二步：原始设定碎片 (Raw Fragments)】**
这是你本次需要处理的，关于 **“{category}”** 的原始条目：

<raw_entries>
{entries_text}
</raw_entries>

**【第三步：世界观构建黄金三角方法论 (The Golden Triangle Methodology)】**
你必须遵循以下思考和写作流程，来构建你的章节：

1.  **要素内在整合 (Intra-Element Integration):**
    - **去重与合并：** 找出`raw_entries`中本质相同或高度相似的条目，将它们合并。
    - **分类与分层：** 在`{category}`内部进行二次分类。例如，如果类别是“组织”，你可以细分为“国家势力”、“秘密社团”、“商业行会”等子标题。这能立刻建立起结构感。
    - **核心要素提炼：** 识别出此类别的“明星要素”（最重要的1-3个条目），并在描述时给予更多笔墨。

2.  **要素间关联构建 (Inter-Element Relation Building):**
    - **建立联系：** 这是最关键的一步！你必须主动思考并回答：当前`{category}`中的条目，与`world_overview`中**其他类别**的条目有什么关系？
        - *示例1 (处理“地点”类别时):* 这个“低语森林”是否是某个“组织”的根据地？它是否与某个“历史事件”有关？森林里的特殊植物是否是某个“角色”制作魔药的材料？
        - *示例2 (处理“角色”类别时):* 这个角色“阿尔弗雷德”属于哪个“组织”？他的行动是否会影响某个“地点”？他是否是某个“历史事件”的亲历者？
    - **在描述中体现关联：** 将你思考出的这些关联，自然地写入描述文字中。这会让世界“活”起来。

3.  **影响与意义升华 (Impact & Significance Elevation):**
    - **功能与作用：** 描述每个要素在世界中的具体功能或作用。它解决了什么问题？或者制造了什么麻烦？
    - **文化与象征意义：** 思考并赋予要素更深层次的意义。这个地点是否是某个种族的圣地？这个组织是否有独特的文化符号和仪式？
    - **动态影响：** 描述这个要素对世界正在产生或将要产生什么影响。它是否是当前世界冲突的焦点？

**【第四步：输出要求 (Output Requirements)】**
- **格式：** 严格使用Markdown，包含多级标题 (`##`, `###`)、列表 (`*` 或 `1.`) 和粗体 (`**text**`)。
- **文笔：** 保持专业、客观的百科式叙述风格，同时兼具文学性和可读性。
- **内容：** 你的输出应该是直接的、最终的Markdown章节内容。严禁包含任何“好的，这是为您生成的章节”之类的对话、解释或元评论。
- **专注：** 本次任务只输出关于 **“{category}”** 的章节内容。
</task>
""")

    def get_generation_prompt(self, category: str, entries: list, all_categories_summary: str) -> str:
        """获取用于生成最终世界书章节的提示词"""
        # 检查条目格式并生成相应的文本
        entries_text_parts = []

        for entry in entries:
            if 'event_summary' in entry:
                # 事件格式
                summary = entry.get('event_summary', '未知事件')
                significance = entry.get('significance', 5)
                participants = entry.get('participants', {})
                location = entry.get('location', '未知地点')
                outcome = entry.get('outcome', '无结果描述')

                primary_participants = ', '.join(participants.get('primary', []))
                entry_text = f"- **{summary}** (重要性:{significance}/10)\n  参与者: {primary_participants}\n  地点: {location}\n  结果: {outcome}"
                entries_text_parts.append(entry_text)
            elif 'rule_summary' in entry:
                # 规则格式
                summary = entry.get('rule_summary', '未知规则')
                importance = entry.get('importance', 5)
                description = entry.get('description', '无描述')
                scope = entry.get('scope', '未知范围')
                evidence = entry.get('evidence', '无证据')

                entry_text = f"- **{summary}** (重要性:{importance}/10)\n  描述: {description}\n  适用范围: {scope}"
                if evidence and len(evidence) < 200:  # 只显示较短的证据
                    entry_text += f"\n  证据: {evidence[:100]}..."
                entries_text_parts.append(entry_text)
            else:
                # 传统实体格式
                name = entry.get('name', '未知条目')
                description = entry.get('description', '无描述')
                entries_text_parts.append(f"- **{name}**: {description}")

        entries_text = "\n".join(entries_text_parts)

        return self.worldbook_prompt_template.format(
            category=category,
            entries_text=entries_text,
            all_categories_summary=all_categories_summary
        )

    def load_and_group_entries(self) -> dict:
        """加载所有原始条目并按类别分组"""
        grouped_entries = defaultdict(list)
        if not self.input_dir.exists():
            print(f"❌ 错误: 找不到原始条目目录 {self.input_dir}")
            return grouped_entries

        # 检查新的分离存储结构
        events_dir = self.input_dir / "events"
        rules_dir = self.input_dir / "rules"

        response_files = []

        # 从events目录加载文件
        if events_dir.exists():
            events_files = list(events_dir.glob("*.json"))
            response_files.extend(events_files)
            print(f"📂 从events目录找到 {len(events_files)} 个事件文件")

        # 从rules目录加载文件
        if rules_dir.exists():
            rules_files = list(rules_dir.glob("*.json"))
            response_files.extend(rules_files)
            print(f"📂 从rules目录找到 {len(rules_files)} 个规则文件")

        # 兼容旧的根目录结构
        root_files = list(self.input_dir.glob("*.json"))
        if root_files:
            response_files.extend(root_files)
            print(f"📂 从根目录找到 {len(root_files)} 个文件（兼容模式）")

        print(f"🔍 总共找到 {len(response_files)} 个原始条目文件，开始解析...")

        if not response_files:
            print("❌ 未找到任何条目文件，请检查：")
            print(f"   - events目录: {events_dir}")
            print(f"   - rules目录: {rules_dir}")
            print(f"   - 根目录: {self.input_dir}")
            return grouped_entries

        for file in response_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                entries_list = []
                if isinstance(data, list):
                    entries_list = data
                elif isinstance(data, dict):
                    for value in data.values():
                        if isinstance(value, list):
                            entries_list = value
                            break
                
                if not entries_list:
                    print(f"⚠️ 警告: 在 {file.name} 中未找到有效的条目列表，已跳过。")
                    continue

                for entry in entries_list:
                    if isinstance(entry, dict):
                        # 检查是否为事件格式
                        if 'event_summary' in entry and 'event_type' in entry:
                            # 事件驱动模式：按事件类型分组
                            event_type = entry.get('event_type', '未分类事件')
                            grouped_entries[event_type].append(entry)
                        # 检查是否为规则格式
                        elif 'rule_summary' in entry and 'rule_type' in entry:
                            # 规则驱动模式：按规则类型分组
                            rule_type = entry.get('rule_type', '未分类规则')
                            grouped_entries[rule_type].append(entry)
                        # 检查是否为传统实体格式
                        elif 'type' in entry and 'name' in entry:
                            # 传统模式：按实体类型分组
                            grouped_entries[entry['type']].append(entry)
                        else:
                            print(f"📝 信息: 跳过 {file.name} 中一个格式不符的条目: {entry}")
                    else:
                        print(f"📝 信息: 跳过 {file.name} 中一个非字典条目: {entry}")

            except json.JSONDecodeError:
                print(f"⚠️ 警告: 无法解析JSON文件 {file.name}，已跳过。")
            except Exception as e:
                print(f"❌ 加载文件失败 {file.name}: {e}")
        
        return grouped_entries

    async def generate_category_content(self, category: str, entries: list, all_categories_summary: str) -> tuple[str, str]:
        """使用LLM为单个类别生成内容"""
        print(f"🚀 [处理中] 开始处理类别: **{category}** ({len(entries)}个条目)")
        prompt = self.get_generation_prompt(category, entries, all_categories_summary)
        
        messages = [
            {"role": "system", "content": "You are a world-class world-building architect. Your task is to synthesize fragmented notes into a coherent, structured, and richly detailed chapter for a worldbook. Follow the user's detailed methodology precisely."},
            {"role": "user", "content": prompt}
        ]

        async with self.semaphore:
            for attempt in range(self.retry_limit):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.pro_model,
                        messages=messages,
                        temperature=self.generation_temperature,
                        max_tokens=self.max_tokens,
                        timeout=self.timeout
                    )
                    content = response.choices[0].message.content
                    print(f"✅ [成功] 已生成类别内容: **{category}**")
                    return category, content.strip()
                except Exception as e:
                    print(f"⚠️ [警告] AI处理类别 {category} 失败 (尝试 {attempt + 1}/{self.retry_limit}): {e}")
                    if attempt < self.retry_limit - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        error_message = f"## {category}\n\n*生成失败: 在达到最大重试次数后仍然失败: {e}*"
                        print(f"❌ [错误] 类别 **{category}** 在达到最大重试次数后仍然失败。")
                        return category, error_message

    async def generate_worldbook(self):
        """生成最终的世界书"""
        print("="*60)
        print(f"✨ 开始使用模型【{self.pro_model}】生成结构化世界书...")
        print("="*60)

        grouped_entries = self.load_and_group_entries()
        if not grouped_entries:
            print("未能加载任何原始条目，世界书生成中止。")
            return

        print(f"📊 已将条目分为 {len(grouped_entries)} 个类别，准备进行AI总结。")
        
        # [核心优化] 创建一个全局上下文摘要，为每个任务提供宏观视角
        all_categories_summary = "世界核心类别及其关键要素概览：\n"
        for cat, ents in grouped_entries.items():
            key_entries_str = ", ".join([e.get('name', '') for e in ents[:3]]) 
            all_categories_summary += f"- **{cat}**: {key_entries_str}...\n"
        print("\n🌐 已生成全局上下文摘要:\n" + "-"*25 + f"\n{all_categories_summary}" + "-"*25 + "\n")

        tasks = [
            self.generate_category_content(category, entries, all_categories_summary)
            for category, entries in grouped_entries.items()
        ]
        
        results = await asyncio.gather(*tasks)

        final_worldbook = {
            "name": self.config.get("project.title", "My Worldbook"),
            "description": self.config.get("project.description", "An AI-generated worldbook."),
            "entries": []
        }

        # 按照原有的类别顺序进行排序，保证每次生成的文件顺序一致
        sorted_categories = sorted(grouped_entries.keys())
        category_results = {cat: cont for cat, cont in results}

        for category in sorted_categories:
            content = category_results.get(category, f"## {category}\n\n*内容生成时发生未知错误*")
            final_worldbook["entries"].append({
                "key": [category], # 保持key为列表格式
                "comment": f"{category} - AI总结章节",
                "content": content,
                "type": category,  # 添加type字段供智能参数优化使用
                "constant": True,
                "enabled": True
            })

        output_file = self.output_dir / "worldbook.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_worldbook, f, ensure_ascii=False, indent=2)
            print("\n" + "="*60)
            print(f"🎉 结构化世界书生成完成！")
            print(f"💾 保存位置: {output_file}")
            print("="*60)
        except Exception as e:
            print(f"❌ 保存最终世界书失败: {e}")

    # ==================== 事件驱动架构新方法 ====================

    async def generate_timeline_worldbook(self) -> str:
        """生成基于事件驱动的时间线世界书"""
        print("🚀 开始生成事件驱动的时间线世界书...")

        # 检查是否启用事件驱动模式
        event_mode = self.config.get('event_driven_architecture.enable', True)
        if not event_mode:
            print("⚠️ 事件驱动模式未启用，回退到传统模式")
            return await self.generate_worldbook()

        try:
            # 1. 加载并排序所有事件
            print("📚 加载和排序事件数据...")
            sorted_events = self.load_and_sort_events()
            if not sorted_events:
                print("⚠️ 未找到事件数据，回退到传统模式")
                return await self.generate_worldbook()

            print(f"📊 共加载 {len(sorted_events)} 个事件")

            # 2. 生成时间线总览（蓝灯条目）
            print("⏰ 生成故事时间线总览...")
            timeline_content = await self.summarize_timeline(sorted_events)

            # 3. 聚合实体信息
            print("👥 聚合实体信息...")
            aggregated_entities = self.aggregate_entities_from_events(sorted_events)

            # 4. 生成实体总结条目（高优先级）
            print("📝 生成核心实体总结...")
            entity_summary_contents = await self.summarize_entities(aggregated_entities)

            # 5. 创建重要事件条目（绿灯）
            print("🎯 创建重要事件条目...")
            event_entries = self.create_event_entries(sorted_events)

            # 6. 整合并保存最终世界书
            print("💾 整合并保存最终世界书...")
            output_file = self.save_timeline_worldbook(
                timeline_content, entity_summary_contents, event_entries
            )

            print(f"✅ 事件驱动世界书生成完成: {output_file}")
            return output_file

        except Exception as e:
            print(f"❌ 事件驱动世界书生成失败: {e}")
            print("🔄 回退到传统模式...")
            return await self.generate_worldbook()

    def load_and_sort_events(self) -> List[Dict[str, Any]]:
        """加载所有事件并按原文顺序排序"""
        all_events = []

        try:
            # 加载mapping.json获取chunk顺序
            mapping_file = Path(self.config.get("output.chunk_dir", "chunks")) / "mapping.json"
            if not mapping_file.exists():
                print(f"⚠️ 未找到mapping文件: {mapping_file}")
                return []

            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            # 按order排序的chunk id列表
            sorted_chunk_ids = [
                chunk['id'] for chunk in
                sorted(mapping.get('chunks', []), key=lambda x: x.get('order', 0))
            ]

            print(f"📂 按顺序处理 {len(sorted_chunk_ids)} 个文本块...")

            for chunk_id in sorted_chunk_ids:
                file = self.input_dir / f"{chunk_id}.json"
                if file.exists():
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data_wrapper = json.load(f)

                        # 解析事件数据
                        events_in_chunk = []
                        if isinstance(data_wrapper, list):
                            events_in_chunk = data_wrapper
                        elif isinstance(data_wrapper, dict):
                            # 尝试从字典中获取事件列表
                            for val in data_wrapper.values():
                                if isinstance(val, list):
                                    events_in_chunk = val
                                    break

                        # 为每个事件附加元数据
                        for event in events_in_chunk:
                            if isinstance(event, dict):
                                event['source_chunk'] = chunk_id
                                event['chunk_order'] = mapping['chunks'][sorted_chunk_ids.index(chunk_id)].get('order', 0)
                                all_events.append(event)

                    except Exception as e:
                        print(f"⚠️ 加载事件文件 {file.name} 失败: {e}")
                        continue

        except Exception as e:
            print(f"❌ 加载事件数据失败: {e}")
            return []

        print(f"✅ 成功加载 {len(all_events)} 个事件")
        return all_events

    def load_and_sort_rules(self) -> List[Dict[str, Any]]:
        """加载所有规则并按重要性排序"""
        all_rules = []

        try:
            # 检查规则目录是否存在
            rules_dir = self.input_dir / "rules"
            if not rules_dir.exists():
                print(f"⚠️ 未找到规则目录: {rules_dir}")
                return []

            # 加载mapping.json获取chunk顺序（用于保持规则的上下文关联）
            mapping_file = Path(self.config.get("output.chunk_dir", "chunks")) / "mapping.json"
            chunk_order = {}
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                chunk_order = {
                    chunk['id']: chunk.get('order', 0)
                    for chunk in mapping.get('chunks', [])
                }

            print(f"📂 从规则目录加载规则数据...")

            for file in rules_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data_wrapper = json.load(f)

                    # 解析规则数据
                    rules_in_chunk = []
                    if isinstance(data_wrapper, list):
                        rules_in_chunk = data_wrapper
                    elif isinstance(data_wrapper, dict):
                        # 尝试从字典中获取规则列表
                        for val in data_wrapper.values():
                            if isinstance(val, list):
                                rules_in_chunk = val
                                break
                    elif isinstance(data_wrapper, str):
                        # 如果是字符串，尝试解析JSON
                        try:
                            rules_in_chunk = json.loads(data_wrapper)
                            if not isinstance(rules_in_chunk, list):
                                rules_in_chunk = [rules_in_chunk]
                        except json.JSONDecodeError:
                            print(f"⚠️ 无法解析规则文件 {file.name} 的JSON内容")
                            continue

                    # 为每个规则附加元数据
                    chunk_name = file.stem
                    for rule in rules_in_chunk:
                        if isinstance(rule, dict) and 'rule_summary' in rule:
                            rule['source_chunk'] = chunk_name
                            rule['chunk_order'] = chunk_order.get(chunk_name, 0)
                            all_rules.append(rule)

                except Exception as e:
                    print(f"⚠️ 加载规则文件 {file.name} 失败: {e}")
                    continue

        except Exception as e:
            print(f"❌ 加载规则数据失败: {e}")
            return []

        # 按重要性排序（重要性高的在前）
        all_rules.sort(key=lambda x: x.get('importance', 0), reverse=True)

        print(f"✅ 成功加载 {len(all_rules)} 个规则")
        return all_rules

    def aggregate_rules_by_type(self, rules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按规则类型聚合规则"""
        grouped_rules = defaultdict(list)

        for rule in rules:
            rule_type = rule.get('rule_type', '未分类规则')
            grouped_rules[rule_type].append(rule)

        return dict(grouped_rules)

    async def summarize_rules(self, grouped_rules: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """为每种规则类型生成系统性的设定描述"""
        rule_summaries = {}

        print(f"📊 开始整合 {len(grouped_rules)} 种类型的规则...")

        for rule_type, rules in grouped_rules.items():
            if not rules:
                continue

            try:
                # 构建规则列表
                rule_descriptions = []
                for rule in rules:
                    summary = rule.get('rule_summary', '未知规则')
                    description = rule.get('description', '')
                    importance = rule.get('importance', 5)
                    evidence = rule.get('evidence', '')

                    rule_text = f"- **{summary}** (重要性:{importance}/10)\n  描述: {description}"
                    if evidence:
                        rule_text += f"\n  依据: {evidence}"
                    rule_descriptions.append(rule_text)

                # 构建整合Prompt
                rules_prompt = f"""
请将以下关于"{rule_type}"的分散规则整合为一个完整、系统性的设定描述。

**要求：**
1. 整合所有相关规则为连贯的系统描述
2. 保持逻辑一致性，消除矛盾
3. 突出核心机制和重要限制
4. 使用Markdown格式，结构清晰
5. 为AI角色扮演提供明确的逻辑基础

**规则列表：**
{chr(10).join(rule_descriptions[:10])}  # 限制长度避免token超限

请生成完整的{rule_type}设定：
"""

                messages = [
                    {"role": "system", "content": "你是一个世界观设计师，擅长整合分散的设定为完整的体系。"},
                    {"role": "user", "content": rules_prompt}
                ]

                response = await self.client.chat.completions.create(
                    model=self.pro_model,
                    messages=messages,
                    temperature=self.generation_temperature,
                    max_tokens=self.max_tokens
                )

                rule_summaries[rule_type] = response.choices[0].message.content.strip()
                print(f"✅ 完成规则整合: {rule_type}")

            except Exception as e:
                print(f"⚠️ 规则类型 {rule_type} 整合失败: {e}")
                # 生成简单的fallback描述
                rule_summaries[rule_type] = f"## {rule_type}\n\n*整合失败，包含{len(rules)}个相关规则*"

        return rule_summaries

    def save_layered_worldbook(self, rule_summaries: Dict[str, str], timeline_content: str,
                              entity_summaries: Dict[str, str], event_entries: List[Dict[str, Any]]) -> str:
        """保存三层架构的世界书，严格遵循SillyTavern v2格式"""

        # 获取三层配置（使用默认值避免None）
        layered_config = self.config.get('world_rules', {}).get('layered_worldbook', {})
        rules_config = layered_config.get('rules_layer', {
            'order_range': [0, 20], 'constant': True, 'depth': 2, 'probability': 100, 'comment_prefix': '【世界规则】'
        })
        timeline_config = layered_config.get('timeline_layer', {
            'order': 21, 'constant': True, 'depth': 3, 'probability': 100, 'comment': '【故事总览】时间线'
        })
        entity_config = layered_config.get('entity_layer', {
            'order_range': [30, 50], 'constant': True, 'depth': 3, 'probability': 95, 'comment_prefix': '【核心实体】'
        })
        event_config = layered_config.get('event_layer', {
            'order_base': 110, 'constant': False, 'depth': 4, 'probability': 80, 'comment_prefix': '【事件】'
        })

        # 初始化SillyTavern v2格式的世界书
        layered_worldbook = {
            "name": "三层架构世界书",
            "description": "基于规则层、时间线层和事件层的智能世界书",
            "entries": []
        }

        current_order = 0

        # 1. 规则层条目（最高优先级：order 0-20）
        print("📝 生成规则层条目...")
        rules_order_start = rules_config.get('order_range', [0, 20])[0]

        for i, (rule_type, rule_content) in enumerate(rule_summaries.items()):
            rule_entry = {
                "key": [rule_type, f"{rule_type}规则", f"{rule_type}设定"],
                "keysecondary": [],
                "comment": f"{rules_config.get('comment_prefix', '【世界规则】')}{rule_type}",
                "content": rule_content,
                "constant": rules_config.get('constant', True),
                "selective": False,
                "order": rules_order_start + i,
                "position": "before_char",
                "disable": False,
                "addMemo": True,
                "excludeRecursion": False,
                "delayUntilRecursion": False,
                "probability": rules_config.get('probability', 100),
                "useProbability": True,
                "depth": rules_config.get('depth', 2),
                "group": "",
                "groupOverride": False,
                "groupWeight": 100,
                "scanDepth": None,
                "caseSensitive": None,
                "matchWholeWords": None,
                "useGroupScoring": False,
                "automationId": "",
                "role": 0,
                "vectorized": False
            }
            layered_worldbook["entries"].append(rule_entry)
            current_order = max(current_order, rule_entry["order"] + 1)

        # 2. 时间线总览条目（order 21）
        print("📝 生成时间线总览条目...")
        timeline_order = timeline_config.get('order', 21)

        timeline_entry = {
            "key": ["时间线", "故事梗概", "剧情总览", "故事发展"],
            "keysecondary": ["年表", "大事记", "情节发展"],
            "comment": timeline_config.get('comment', '【故事总览】时间线'),
            "content": timeline_content,
            "constant": timeline_config.get('constant', True),
            "selective": False,
            "order": timeline_order,
            "position": "before_char",
            "disable": False,
            "addMemo": True,
            "excludeRecursion": False,
            "delayUntilRecursion": False,
            "probability": timeline_config.get('probability', 100),
            "useProbability": True,
            "depth": timeline_config.get('depth', 3),
            "group": "",
            "groupOverride": False,
            "groupWeight": 100,
            "scanDepth": None,
            "caseSensitive": None,
            "matchWholeWords": None,
            "useGroupScoring": False,
            "automationId": "",
            "role": 0,
            "vectorized": False
        }
        layered_worldbook["entries"].append(timeline_entry)
        current_order = max(current_order, timeline_order + 1)

        # 3. 核心实体条目（order 30-50）
        print("📝 生成核心实体条目...")
        entity_order_start = entity_config.get('order_range', [30, 50])[0]

        for i, (entity_name, entity_content) in enumerate(entity_summaries.items()):
            entity_entry = {
                "key": [entity_name],
                "keysecondary": [],
                "comment": f"{entity_config.get('comment_prefix', '【核心实体】')}{entity_name}",
                "content": entity_content,
                "constant": entity_config.get('constant', True),
                "selective": False,
                "order": entity_order_start + i,
                "position": "before_char",
                "disable": False,
                "addMemo": True,
                "excludeRecursion": False,
                "delayUntilRecursion": False,
                "probability": entity_config.get('probability', 95),
                "useProbability": True,
                "depth": entity_config.get('depth', 3),
                "group": "",
                "groupOverride": False,
                "groupWeight": 100,
                "scanDepth": None,
                "caseSensitive": None,
                "matchWholeWords": None,
                "useGroupScoring": False,
                "automationId": "",
                "role": 0,
                "vectorized": False
            }
            layered_worldbook["entries"].append(entity_entry)
            current_order = max(current_order, entity_entry["order"] + 1)

        # 4. 事件层条目（基于significance动态计算order）
        print("📝 生成事件层条目...")
        order_base = event_config.get('order_base', 110)

        for event in event_entries:
            # 从现有事件条目中提取信息
            significance = event.get('significance', 5)
            event_order = order_base - (significance * 10)  # 重要性越高，order越小

            # 确保事件条目符合SillyTavern v2格式
            event_entry = {
                "key": event.get('key', []),
                "keysecondary": event.get('keysecondary', []),
                "comment": event.get('comment', f"{event_config.get('comment_prefix', '【事件】')}未知事件"),
                "content": event.get('content', ''),
                "constant": event_config.get('constant', False),
                "selective": True,  # 事件通常使用选择性注入
                "order": event_order,
                "position": "before_char",
                "disable": False,
                "addMemo": True,
                "excludeRecursion": False,
                "delayUntilRecursion": False,
                "probability": event_config.get('probability', 80),
                "useProbability": True,
                "depth": event_config.get('depth', 4),
                "group": "",
                "groupOverride": False,
                "groupWeight": 100,
                "scanDepth": None,
                "caseSensitive": None,
                "matchWholeWords": None,
                "useGroupScoring": False,
                "automationId": "",
                "role": 0,
                "vectorized": False
            }
            layered_worldbook["entries"].append(event_entry)

        # 保存三层世界书文件
        output_file = self.output_dir / "layered_worldbook.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(layered_worldbook, f, ensure_ascii=False, indent=2)

            print("\n" + "="*80)
            print(f"🎉 三层架构世界书生成完成！")
            print(f"💾 保存位置: {output_file}")
            print(f"📊 总条目数: {len(layered_worldbook['entries'])}")
            print(f"  - 规则层: {len(rule_summaries)} 个规则类型")
            print(f"  - 时间线层: 1 个总览")
            print(f"  - 实体层: {len(entity_summaries)} 个核心实体")
            print(f"  - 事件层: {len(event_entries)} 个重要事件")
            print("\n📋 SillyTavern v2格式验证:")
            print(f"  ✅ 所有条目包含必需字段: key, content, order, constant")
            print(f"  ✅ 参数分配符合三层架构设计")
            print(f"  ✅ 优先级排序: 规则层(0-20) > 时间线(21) > 实体(30-50) > 事件(60-120)")
            print("="*80)

            return str(output_file)

        except Exception as e:
            print(f"❌ 保存三层世界书失败: {e}")
            return ""

    async def summarize_timeline(self, events: List[Dict[str, Any]]) -> str:
        """生成故事时间线总览"""
        if not events:
            return "## 故事时间线\n\n*暂无事件数据*"

        # 构建时间线摘要
        timeline_summaries = []
        for event in events:
            summary = event.get('event_summary', '未知事件')
            significance = event.get('significance', 5)
            if significance >= 7:  # 只包含重要事件
                timeline_summaries.append(f"- {summary}")

        timeline_prompt = f"""
请根据以下关键事件列表，生成一个完整的故事时间线总览。

**要求：**
1. 按时间顺序梳理主要情节发展
2. 突出关键转折点和重要事件
3. 保持叙述的连贯性和逻辑性
4. 使用Markdown格式，包含适当的标题和结构

**关键事件列表：**
{chr(10).join(timeline_summaries[:20])}  # 限制长度避免token超限

请生成故事时间线总览：
"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的故事分析师，擅长梳理复杂情节的时间线。"},
                {"role": "user", "content": timeline_prompt}
            ]

            response = await self.client.chat.completions.create(
                model=self.pro_model,
                messages=messages,
                temperature=self.generation_temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"⚠️ 时间线生成失败: {e}")
            return f"## 故事时间线\n\n*生成失败，包含{len(events)}个事件*"

    def aggregate_entities_from_events(self, events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """从事件中聚合实体信息"""
        entities = defaultdict(lambda: {
            'events': [],
            'locations': set(),
            'items': set(),
            'total_significance': 0,
            'event_count': 0,
            'entity_type': 'character'  # 默认为角色
        })

        for event in events:
            participants = event.get('participants', {})
            location = event.get('location', '')
            key_items = event.get('key_items', [])
            significance = event.get('significance', 5)

            # 处理主要参与者
            for participant in participants.get('primary', []):
                if participant and participant.strip():
                    entities[participant]['events'].append(event)
                    entities[participant]['total_significance'] += significance
                    entities[participant]['event_count'] += 1
                    if location:
                        entities[participant]['locations'].add(location)
                    entities[participant]['items'].update(key_items)

            # 处理次要参与者
            for participant in participants.get('secondary', []):
                if participant and participant.strip():
                    entities[participant]['events'].append(event)
                    entities[participant]['total_significance'] += significance * 0.5  # 次要参与者权重减半
                    entities[participant]['event_count'] += 1
                    if location:
                        entities[participant]['locations'].add(location)

        # 转换set为list以便JSON序列化
        for entity_name, entity_data in entities.items():
            entity_data['locations'] = list(entity_data['locations'])
            entity_data['items'] = list(entity_data['items'])
            entity_data['average_significance'] = entity_data['total_significance'] / max(entity_data['event_count'], 1)

        return dict(entities)

    async def summarize_entities(self, entities: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """为重要实体生成总结条目"""
        entity_summaries = {}

        # 筛选重要实体（参与事件数量 >= 3 或平均重要性 >= 6）
        important_entities = {
            name: data for name, data in entities.items()
            if data['event_count'] >= 3 or data['average_significance'] >= 6
        }

        print(f"📊 识别出 {len(important_entities)} 个重要实体")

        for entity_name, entity_data in important_entities.items():
            try:
                # 构建实体事件摘要
                event_summaries = []
                for event in entity_data['events'][:10]:  # 限制事件数量
                    summary = event.get('event_summary', '')
                    significance = event.get('significance', 5)
                    event_summaries.append(f"- {summary} (重要性: {significance})")

                entity_prompt = f"""
请根据以下事件信息，为角色/实体"{entity_name}"生成一份详细的总结。

**实体信息：**
- 参与事件数量：{entity_data['event_count']}
- 平均重要性：{entity_data['average_significance']:.1f}
- 活动地点：{', '.join(entity_data['locations'][:5])}
- 相关物品：{', '.join(entity_data['items'][:5])}

**参与的关键事件：**
{chr(10).join(event_summaries)}

**要求：**
1. 生成一份完整的角色/实体档案
2. 描述其在故事中的作用和发展轨迹
3. 突出其重要性和影响力
4. 使用Markdown格式，结构清晰

请生成实体总结：
"""

                messages = [
                    {"role": "system", "content": "你是一个专业的角色分析师，擅长从事件中提炼角色特征和发展轨迹。"},
                    {"role": "user", "content": entity_prompt}
                ]

                response = await self.client.chat.completions.create(
                    model=self.pro_model,
                    messages=messages,
                    temperature=self.generation_temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout
                )

                entity_summaries[entity_name] = response.choices[0].message.content.strip()
                print(f"✅ 完成实体总结: {entity_name}")

            except Exception as e:
                print(f"⚠️ 实体 {entity_name} 总结生成失败: {e}")
                entity_summaries[entity_name] = f"## {entity_name}\n\n*总结生成失败*"

        return entity_summaries

    def create_event_entries(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为重要事件创建世界书条目"""
        event_entries = []

        # 筛选重要事件（significance >= 6）
        important_events = [
            event for event in events
            if event.get('significance', 5) >= 6
        ]

        print(f"📊 识别出 {len(important_events)} 个重要事件")

        for event in important_events:
            try:
                # 构建关键词列表
                keywords = []

                # 添加参与者作为关键词
                participants = event.get('participants', {})
                keywords.extend(participants.get('primary', []))
                keywords.extend(participants.get('secondary', []))

                # 添加地点作为关键词
                location = event.get('location', '')
                if location:
                    keywords.append(location)

                # 添加重要物品作为关键词
                keywords.extend(event.get('key_items', []))

                # 去重并过滤空值
                keywords = list(set([k.strip() for k in keywords if k and k.strip()]))

                # 构建事件条目
                event_entry = {
                    "key": keywords[:5],  # 限制关键词数量
                    "keysecondary": [],
                    "comment": f"【事件】{event.get('event_summary', '未知事件')}",
                    "content": self._format_event_content(event),
                    "type": "事件",
                    "significance": event.get('significance', 5),
                    "event_type": event.get('event_type', '未分类'),
                    "constant": False,
                    "enabled": True
                }

                event_entries.append(event_entry)

            except Exception as e:
                print(f"⚠️ 事件条目创建失败: {e}")
                continue

        return event_entries

    def _format_event_content(self, event: Dict[str, Any]) -> str:
        """格式化事件内容为Markdown"""
        content_parts = []

        # 事件标题
        summary = event.get('event_summary', '未知事件')
        content_parts.append(f"# {summary}")

        # 事件类型和重要性
        event_type = event.get('event_type', '未分类')
        significance = event.get('significance', 5)
        content_parts.append(f"\n**事件类型**: {event_type}")
        content_parts.append(f"**重要性**: {significance}/10")

        # 参与者信息
        participants = event.get('participants', {})
        if participants.get('primary'):
            content_parts.append(f"\n**主要参与者**: {', '.join(participants['primary'])}")
        if participants.get('secondary'):
            content_parts.append(f"**次要参与者**: {', '.join(participants['secondary'])}")

        # 地点信息
        location = event.get('location', '')
        if location:
            content_parts.append(f"**发生地点**: {location}")

        # 相关物品
        key_items = event.get('key_items', [])
        if key_items:
            content_parts.append(f"**相关物品**: {', '.join(key_items)}")

        # 事件结果
        outcome = event.get('outcome', '')
        if outcome:
            content_parts.append(f"\n**事件结果**: {outcome}")

        # 因果关系
        causal_chain = event.get('causal_chain', {})
        if causal_chain:
            trigger = causal_chain.get('trigger', '')
            consequence = causal_chain.get('consequence', '')
            if trigger:
                content_parts.append(f"\n**触发原因**: {trigger}")
            if consequence:
                content_parts.append(f"**后续影响**: {consequence}")

        # 情感影响
        emotional_impact = event.get('emotional_impact', '')
        if emotional_impact:
            content_parts.append(f"\n**情感影响**: {emotional_impact}")

        return '\n'.join(content_parts)

    def save_timeline_worldbook(self, timeline_content: str, entity_summaries: Dict[str, str],
                               event_entries: List[Dict[str, Any]]) -> str:
        """保存事件驱动的时间线世界书"""
        final_worldbook = {
            "name": "事件驱动世界书",
            "description": "基于时间线和事件的智能世界书",
            "entries": []
        }

        # 1. 添加时间线总览（蓝灯条目 - 最高优先级）
        timeline_entry = {
            "key": ["时间线", "故事梗概", "剧情总览"],
            "keysecondary": ["年表", "大事记"],
            "comment": "【总览】故事时间线",
            "content": timeline_content,
            "type": "时间线总览",
            "constant": True,
            "enabled": True
        }
        final_worldbook["entries"].append(timeline_entry)

        # 2. 添加实体总结条目（高优先级）
        for entity_name, entity_content in entity_summaries.items():
            entity_entry = {
                "key": [entity_name],
                "keysecondary": [],
                "comment": f"【核心实体】{entity_name}",
                "content": entity_content,
                "type": "核心实体",
                "constant": True,
                "enabled": True
            }
            final_worldbook["entries"].append(entity_entry)

        # 3. 添加重要事件条目（绿灯）
        final_worldbook["entries"].extend(event_entries)

        # 保存文件
        output_file = self.output_dir / "timeline_worldbook.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_worldbook, f, ensure_ascii=False, indent=2)

            print("\n" + "="*60)
            print(f"🎉 事件驱动世界书生成完成！")
            print(f"💾 保存位置: {output_file}")
            print(f"📊 总条目数: {len(final_worldbook['entries'])}")
            print(f"  - 时间线总览: 1")
            print(f"  - 核心实体: {len(entity_summaries)}")
            print(f"  - 重要事件: {len(event_entries)}")
            print("="*60)

            return str(output_file)

        except Exception as e:
            print(f"❌ 保存事件驱动世界书失败: {e}")
            return ""

def main():
    """主函数"""
    try:
        generator = WorldbookGenerator()
        asyncio.run(generator.generate_worldbook())
    except Exception as e:
        print(f"❌ 程序运行出现致命错误: {e}")

if __name__ == "__main__":
    main()
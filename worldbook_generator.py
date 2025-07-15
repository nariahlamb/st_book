#!/usr/bin/env python3
"""
世界书生成器 - 负责将原始条目升华为结构化的世界书
版本: 2.0 (采用全局上下文和世界观构建方法论)
"""

import json
import asyncio
from pathlib import Path
from collections import defaultdict
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
        # 使用.get()方法安全地访问字典键，并提供默认值
        entries_text = "\n".join([f"- **{entry.get('name', '未知条目')}**: {entry.get('description', '无描述')}" for entry in entries])

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

        response_files = list(self.input_dir.glob("*.json"))
        print(f"🔍 找到 {len(response_files)} 个原始条目文件，开始解析...")
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
                    if isinstance(entry, dict) and 'type' in entry and 'name' in entry:
                        grouped_entries[entry['type']].append(entry)
                    else:
                        print(f"📝 信息: 跳过 {file.name} 中一个格式不符的条目: {entry}")

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

def main():
    """主函数"""
    try:
        generator = WorldbookGenerator()
        asyncio.run(generator.generate_worldbook())
    except Exception as e:
        print(f"❌ 程序运行出现致命错误: {e}")

if __name__ == "__main__":
    main()

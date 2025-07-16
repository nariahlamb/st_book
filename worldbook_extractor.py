#!/usr/bin/env python3
"""
世界书条目提取器 - 负责从文本块中提取原始设定条目并分类
"""

import json
import asyncio
from pathlib import Path
from openai import AsyncOpenAI
from project_config import get_config

class WorldbookExtractor:
    """使用基础模型提取和分类世界书条目"""

    def __init__(self):
        self.config = get_config()
        self.chunks_dir = Path(self.config.get("output.chunk_dir", "chunks"))
        self.output_dir = Path(self.config.get("output.wb_responses_dir", "wb_responses"))
        self.output_dir.mkdir(exist_ok=True)

        # 创建子目录用于分离存储事件和规则数据
        self.events_dir = self.output_dir / "events"
        self.rules_dir = self.output_dir / "rules"
        self.events_dir.mkdir(exist_ok=True)
        self.rules_dir.mkdir(exist_ok=True)

        # 使用新的配置系统
        model_config = self.config.get_model_config()
        api_config = self.config.get_api_config()

        self.model = model_config.get("extraction_model", "gemini-2.5-flash")
        self.worldbook_temperature = model_config.get("worldbook_temperature", 0.2)
        self.max_tokens = int(model_config.get("max_tokens", 60000))

        # 性能配置
        self.max_concurrent = int(self.config.get("performance.max_concurrent", 1))
        self.retry_limit = int(self.config.get("performance.retry_limit", 3))
        self.retry_delay = int(self.config.get("performance.retry_delay", 10))
        self.rate_limit_delay = int(self.config.get("performance.rate_limit_delay", 5))
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # 初始化OpenAI客户端
        api_key = api_config.get("api_key")
        if not api_key:
            raise ValueError("❌ 找不到 API 金鑰，請在 config.yaml 中設定 'api.api_key'")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_config.get("api_base"),
            timeout=int(model_config.get("timeout", 300))
        )

    def get_extraction_prompt(self, chunk_metadata: dict = None) -> str:
        """获取用于提取的提示词（支持事件驱动和实体提取两种模式）"""
        # 检查是否启用事件驱动模式
        event_mode = self.config.get('event_driven_architecture.enable', True)

        if event_mode:
            return self._get_event_extraction_prompt(chunk_metadata)
        else:
            return self._get_entity_extraction_prompt()

    def _get_event_extraction_prompt(self, chunk_metadata: dict = None) -> str:
        """获取事件驱动的提取提示词"""
        # 构建时序上下文信息
        timeline_context = ""
        if chunk_metadata:
            timeline_pos = chunk_metadata.get('estimated_timeline_position', '未知')
            chapter_title = chunk_metadata.get('chapter_title', '未知章节')
            narrative_context = chunk_metadata.get('narrative_context', {})
            emotional_tone = narrative_context.get('emotional_tone', '中性')

            timeline_context = f"""
【时序上下文】
- 故事位置：{timeline_pos}
- 章节标题：{chapter_title}
- 情感基调：{emotional_tone}
- 对话密度：{'高' if narrative_context.get('has_dialogue') else '低'}
- 动作密度：{'高' if narrative_context.get('has_action') else '低'}
"""

        return self.config.get("event_driven_architecture.event_extraction.prompt", f"""
你是一个专业的故事分析师，请从以下文本中提取关键事件信息。

{timeline_context}

**提取要求**
1. **事件识别**：提取推动情节发展的关键事件，而非静态描述
2. **重要性评分**：为每个事件评分1-10分（10分=改变主线剧情，1分=背景细节）
3. **参与者分析**：识别事件的主要参与者和次要参与者
4. **因果关系**：分析事件的起因和结果
5. **时空定位**：确定事件发生的地点和时间

**事件分类标准**
- 战斗事件：武力冲突、决斗、战争
- 修炼突破：境界提升、功法领悟、能力觉醒
- 情感转折：关系变化、情感发展、心理转变
- 阴谋揭露：秘密暴露、真相发现、计谋败露
- 势力变动：组织变化、权力转移、联盟建立
- 宝物获得：重要物品、功法秘籍、神器发现
- 地点探索：新区域发现、环境变化、地理事件
- 关系建立：结盟、师徒、友谊、敌对关系形成
- 危机解决：困境突破、问题解决、威胁消除
- 背景揭示：世界观展示、历史回顾、设定说明

**输出格式**
请输出JSON数组，每个事件包含以下字段：
[
  {{
    "event_summary": "简洁的事件描述（20字以内）",
    "event_type": "事件分类（从上述分类中选择）",
    "participants": {{
      "primary": ["主要参与者1", "主要参与者2"],
      "secondary": ["次要参与者1", "次要参与者2"]
    }},
    "location": "事件发生地点",
    "key_items": ["涉及的重要物品或概念"],
    "significance": 8,
    "outcome": "事件结果和影响",
    "causal_chain": {{
      "trigger": "事件触发原因",
      "consequence": "后续影响"
    }},
    "timeline_position": "在故事中的时间位置",
    "emotional_impact": "情感影响程度（高/中/低）"
  }}
]

**小说段落:**
""")

    def _get_entity_extraction_prompt(self) -> str:
        """获取传统实体提取提示词（向后兼容）"""
        return self.config.get("worldbook.extraction_prompt", """
你是一个世界观分析AI，任务是从以下小说段落中，提取所有重要的世界观设定条目。

**提取要求:**
1.  **识别关键条目**: 找出所有涉及地点、组织、种族、关键物品、特殊能力、历史事件或独特概念的专有名词。
2.  **自动分类**: 为每个条目确定一个最合适的类别。类别应该是单数名词，例如：`地点`, `组织`, `种族`, `物品`, `能力`, `事件`, `概念`。
3.  **简洁描述**: 用一两句话简洁地描述每个条目。
4.  **JSON输出**: 必须以一个JSON数组的格式输出，不要包含任何其他文字或markdown标记。

**输出格式示例:**
[
  {
    "name": "红月之森",
    "type": "地点",
    "description": "一片永远被红色月光笼罩的森林，是精灵族的圣地。"
  },
  {
    "name": "暗影兄弟会",
    "type": "组织",
    "description": "一个活动在王国地下的秘密刺客公会。"
  },
  {
    "name": "龙裔",
    "type": "种族",
    "description": "拥有巨龙血脉的稀有类人种族，能够使用龙语魔法。"
  }
]

**小说段落:**
""")

    def get_rules_extraction_prompt(self, chunk_metadata: dict = None) -> str:
        """获取世界规则提取的提示词"""
        # 构建时序上下文信息
        timeline_context = ""
        if chunk_metadata:
            timeline_pos = chunk_metadata.get('estimated_timeline_position', '未知')
            chapter_title = chunk_metadata.get('chapter_title', '未知章节')

            timeline_context = f"""
【时序上下文】
- 故事位置：{timeline_pos}
- 章节标题：{chapter_title}
"""

        return self.config.get("world_rules.rule_extraction.extraction_prompt", f"""
你是一个世界观架构师，专门从小说文本中提取构成世界基础的规则和设定。

{timeline_context}

**提取目标**：识别文本中体现的世界运行规则，而非具体事件。

**规则分类**：
- 物理法则：重力、时间、空间等基础物理规律
- 魔法体系：魔法原理、法术分类、魔力来源、施法规则
- 修炼体系：境界等级、修炼方法、突破条件、能力获得
- 神明设定：神祇体系、神力规则、信仰机制、神迹表现
- 种族设定：各种族特征、天赋能力、文化背景、生理特点
- 社会规则：政治制度、法律体系、社会习俗、等级秩序
- 地理背景：世界地理、气候环境、地域特色、空间结构
- 历史背景：重大历史、时代变迁、文明发展、传说起源
- 经济体系：货币制度、贸易规则、资源分配、价值体系
- 技术水平：科技发展、工艺水平、创新能力、技术限制

**输出格式**：
[
  {{
    "rule_summary": "规则的简洁描述（20字以内）",
    "rule_type": "规则分类（从上述分类中选择）",
    "description": "规则的详细说明和运行机制",
    "importance": 8,
    "evidence": "文本中体现此规则的具体证据",
    "implications": "此规则对世界和角色的影响",
    "scope": "规则的适用范围（全世界/特定地区/特定群体）"
  }}
]

**小说段落:**
""")

    def _load_chunk_metadata(self, chunk_name: str) -> dict:
        """加载文本块的时序元数据"""
        try:
            mapping_file = self.chunks_dir / "mapping.json"
            if not mapping_file.exists():
                return {}

            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)

            # 查找对应的chunk信息
            for chunk_info in mapping_data.get('chunks', []):
                if chunk_info.get('id') == chunk_name:
                    return chunk_info

            return {}
        except Exception as e:
            print(f"[WARNING] 加载时序元数据失败: {e}")
            return {}

    async def extract_from_chunk(self, chunk_file: Path, idx: int, total: int) -> None:
        """从单个文本块中提取世界书条目（支持双重提取：事件+规则）"""
        chunk_name = chunk_file.stem

        # 检查是否启用规则提取
        rules_enabled = self.config.get('world_rules.enable_extraction', True)

        # 检查输出文件是否已存在
        events_output = self.events_dir / f"{chunk_name}.json"
        rules_output = self.rules_dir / f"{chunk_name}.json" if rules_enabled else None

        # 检查是否需要跳过
        events_exists = events_output.exists()
        rules_exists = rules_output.exists() if rules_output else True

        if events_exists and rules_exists:
            print(f"[SKIP] [{idx}/{total}] {chunk_name} 已提取，跳过")
            return

        print(f"[PROCESS] [{idx}/{total}] 开始提取: {chunk_name}")
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_text = f.read()
        except Exception as e:
            print(f"[ERROR] [{idx}/{total}] 读取 {chunk_file.name} 失败: {e}")
            return

        # 加载时序元数据
        chunk_metadata = self._load_chunk_metadata(chunk_name)

        # 并行执行事件和规则提取
        tasks = []

        if not events_exists:
            print(f"[DEBUG] [{idx}/{total}] {chunk_name} 开始事件提取...")
            tasks.append(self._extract_events(chunk_text, chunk_metadata, events_output, chunk_name, idx, total))

        if rules_enabled and rules_output and not rules_exists:
            print(f"[DEBUG] [{idx}/{total}] {chunk_name} 开始规则提取...")
            tasks.append(self._extract_rules(chunk_text, chunk_metadata, rules_output, chunk_name, idx, total))
        elif not rules_enabled:
            print(f"[DEBUG] [{idx}/{total}] {chunk_name} 规则提取已禁用")
        elif rules_exists:
            print(f"[DEBUG] [{idx}/{total}] {chunk_name} 规则文件已存在，跳过")

        # 并行执行所有提取任务
        if tasks:
            await asyncio.gather(*tasks)
            print(f"[COMPLETE] [{idx}/{total}] {chunk_name} 所有提取任务完成")

    async def _extract_events(self, chunk_text: str, chunk_metadata: dict, output_file: Path,
                             chunk_name: str, idx: int, total: int) -> None:
        """提取事件数据（带重试机制）"""
        prompt = self.get_extraction_prompt(chunk_metadata) + chunk_text
        messages = [
            {"role": "system", "content": "你是一个专业的故事分析师。"},
            {"role": "user", "content": prompt}
        ]

        async with self.semaphore:
            for attempt in range(1, self.retry_limit + 1):
                try:
                    print(f"[PROCESS] [{idx}/{total}] {chunk_name} 事件提取（第 {attempt} 次）")

                    # API调用前等待，避免限流
                    if attempt > 1:
                        await asyncio.sleep(self.rate_limit_delay)

                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.worldbook_temperature,
                        max_tokens=self.max_tokens
                    )

                    response_text = response.choices[0].message.content
                    if not response_text:
                        raise ValueError("API 返回空内容")

                    # 清理响应文本，提取纯JSON
                    cleaned_json = self._extract_json_from_response(response_text.strip())

                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(cleaned_json)

                    print(f"[SUCCESS] [{idx}/{total}] {chunk_name} 事件提取完成")
                    return  # 成功后退出

                except Exception as e:
                    err_info = str(e)
                    print(f"[WARNING] [{idx}/{total}] {chunk_name} 事件提取失败（第 {attempt} 次）：{err_info}")

                    # 处理限流错误
                    if "rate limit" in err_info.lower() or "429" in err_info:
                        print(f"[WAIT] API 限流，等待 {self.retry_delay * attempt} 秒")
                        await asyncio.sleep(self.retry_delay * attempt)
                    elif attempt < self.retry_limit:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        print(f"[ERROR] [{idx}/{total}] {chunk_name} 事件提取在达到最大重试次数后仍然失败")
                        # 创建空的JSON文件作为fallback
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write('[]')
                        break

    async def _extract_rules(self, chunk_text: str, chunk_metadata: dict, output_file: Path,
                            chunk_name: str, idx: int, total: int) -> None:
        """提取规则数据（带重试机制）"""
        prompt = self.get_rules_extraction_prompt(chunk_metadata) + chunk_text
        messages = [
            {"role": "system", "content": "你是一个世界观架构师。"},
            {"role": "user", "content": prompt}
        ]

        async with self.semaphore:
            for attempt in range(1, self.retry_limit + 1):
                try:
                    print(f"[PROCESS] [{idx}/{total}] {chunk_name} 规则提取（第 {attempt} 次）")

                    # API调用前等待，避免限流
                    if attempt > 1:
                        await asyncio.sleep(self.rate_limit_delay)

                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.worldbook_temperature,
                        max_tokens=self.max_tokens
                    )

                    response_text = response.choices[0].message.content
                    if not response_text:
                        raise ValueError("API 返回空内容")

                    # 清理响应文本，提取纯JSON
                    cleaned_json = self._extract_json_from_response(response_text.strip())

                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(cleaned_json)

                    print(f"[SUCCESS] [{idx}/{total}] {chunk_name} 规则提取完成")
                    return  # 成功后退出

                except Exception as e:
                    err_info = str(e)
                    print(f"[WARNING] [{idx}/{total}] {chunk_name} 规则提取失败（第 {attempt} 次）：{err_info}")

                    # 处理限流错误
                    if "rate limit" in err_info.lower() or "429" in err_info:
                        print(f"[WAIT] API 限流，等待 {self.retry_delay * attempt} 秒")
                        await asyncio.sleep(self.retry_delay * attempt)
                    elif attempt < self.retry_limit:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        print(f"[ERROR] [{idx}/{total}] {chunk_name} 规则提取在达到最大重试次数后仍然失败")
                        # 创建空的JSON文件作为fallback
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write('[]')
                        break

    def _extract_json_from_response(self, response_text: str) -> str:
        """从LLM响应中提取纯JSON内容"""
        try:
            # 移除常见的LLM响应前缀
            lines = response_text.strip().split('\n')

            # 查找JSON开始位置
            json_start = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('[') or stripped.startswith('{'):
                    json_start = i
                    break
                elif '```json' in stripped.lower():
                    json_start = i + 1
                    break

            if json_start == -1:
                # 如果没找到明显的JSON开始，尝试查找包含JSON的行
                for i, line in enumerate(lines):
                    if '[' in line or '{' in line:
                        json_start = i
                        break

            if json_start == -1:
                print("⚠️ 未找到JSON开始位置，返回原始响应")
                return response_text

            # 查找JSON结束位置
            json_end = len(lines)
            for i in range(json_start, len(lines)):
                stripped = lines[i].strip()
                if '```' in stripped and i > json_start:
                    json_end = i
                    break

            # 提取JSON部分
            json_lines = lines[json_start:json_end]
            json_text = '\n'.join(json_lines)

            # 验证JSON格式
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                # 如果解析失败，尝试修复常见问题
                return self._fix_common_json_issues(json_text)

        except Exception as e:
            print(f"⚠️ JSON提取失败: {e}")
            return response_text

    def _fix_common_json_issues(self, json_text: str) -> str:
        """修复常见的JSON格式问题"""
        try:
            # 移除多余的逗号
            json_text = json_text.replace(',]', ']').replace(',}', '}')

            # 尝试解析修复后的JSON
            json.loads(json_text)
            return json_text

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON修复失败: {e}")
            # 返回一个空的JSON数组作为fallback
            return '[]'

    async def extract_all(self):
        """提取所有文本块中的世界书条目"""
        print("="*60)
        print(f"开始使用 {self.model} 提取世界书原始条目...")
        print("="*60)

        if not self.chunks_dir.exists():
            print(f"错误: 找不到文本块目录 {self.chunks_dir}")
            return

        chunk_files = sorted(list(self.chunks_dir.glob("chunk_*.txt")))
        if not chunk_files:
            print(f"在 {self.chunks_dir} 中没有找到文本块文件。")
            return
            
        print(f"找到 {len(chunk_files)} 个文本块，准备进行提取。")

        tasks = [
            self.extract_from_chunk(chunk_file, idx + 1, len(chunk_files))
            for idx, chunk_file in enumerate(chunk_files)
        ]
        await asyncio.gather(*tasks)

        print("\n原始世界书条目提取完成！")
        print(f"保存位置: {self.output_dir}")

def main():
    """主函数"""
    extractor = WorldbookExtractor()
    asyncio.run(extractor.extract_all())

if __name__ == "__main__":
    main()

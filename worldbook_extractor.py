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

        # 使用新的配置系统
        model_config = self.config.get_model_config()
        api_config = self.config.get_api_config()

        self.model = model_config.get("extraction_model", "gemini-2.5-flash")
        self.worldbook_temperature = model_config.get("worldbook_temperature", 0.2)
        self.max_tokens = int(model_config.get("max_tokens", 60000))

        # 性能配置
        self.max_concurrent = int(self.config.get("performance.max_concurrent", 1))
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

    def get_extraction_prompt(self) -> str:
        """获取用于提取和分类世界书条目的提示词"""
        # 允许用户在config.yaml中自定义此提示词
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

    async def extract_from_chunk(self, chunk_file: Path, idx: int, total: int) -> None:
        """从单个文本块中提取世界书条目"""
        chunk_name = chunk_file.stem
        output_file = self.output_dir / f"{chunk_name}.json"

        if output_file.exists():
            print(f"[SKIP] [{idx}/{total}] {chunk_name} 已提取，跳过")
            return

        print(f"[PROCESS] [{idx}/{total}] 开始提取: {chunk_name}")
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_text = f.read()
        except Exception as e:
            print(f"[ERROR] [{idx}/{total}] 读取 {chunk_file.name} 失败: {e}")
            return

        prompt = self.get_extraction_prompt() + chunk_text
        messages = [
            {"role": "system", "content": "你是一个世界观分析AI。"},
            {"role": "user", "content": prompt}
        ]

        async with self.semaphore:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.worldbook_temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"}
                )
                
                llm_output = response.choices[0].message.content
                # 直接保存JSON字符串，无需解析
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(llm_output)

                print(f"[SUCCESS] [{idx}/{total}] 已提取并保存: {output_file.name}")

            except Exception as e:
                print(f"[ERROR] [{idx}/{total}] AI处理或保存 {chunk_name} 失败: {e}")

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

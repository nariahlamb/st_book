#!/usr/bin/env python3
"""
SillyTavern 角色卡创建器 - AI增强版
"""

import json
import asyncio
from pathlib import Path
from openai import AsyncOpenAI
from project_config import get_config

class CardCreator:
    """使用Pro模型智能生成角色卡"""

    def __init__(self):
        self.config = get_config()
        self.roles_dir = Path(self.config.get("output.roles_json_dir", "roles_json"))
        self.cards_dir = Path(self.config.get("output.cards_dir", "cards"))
        self.cards_dir.mkdir(exist_ok=True)

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

    def get_card_generation_prompt(self, raw_data: dict) -> str:
        """获取用于生成最终角色卡的提示词"""
        # 将原始数据格式化为字符串
        raw_text = json.dumps(raw_data, ensure_ascii=False, indent=2)

        return f"""你是一位专业的角色设定作家和SillyTavern角色卡制作专家。
你的任务是分析以下零散、重复的原始角色数据，将其提炼、润色并整合成一张高质量的、连贯的SillyTavern角色卡。

**原始数据:**
```json
{raw_text}
```

**处理要求:**
1.  **description**: 综合所有‘description’和‘scenario’的内容，创作一段生动、详细、连贯的角色描述。包括角色的外貌、背景故事、关键能力和所处的世界环境。消除矛盾，补充细节，使其读起来像一个完整的人物传记。
2.  **personality**: 深入分析所有‘personality’条目，总结出角色最核心、最一致的性格特点。不要简单罗列，要用富有文采的语言进行概括和深化，解释这些性格特征是如何相互影响的。
3.  **first_mes**: 基于角色的性格和背景，创作一句极具代表性、能立刻吸引用户注意力的开场白。
4.  **alternate_greetings**: 创作三句不同风格的、符合角色身份和性格的备选开场白。
5.  **tags**: 根据角色描述和性格，提取5个最相关的核心标签（例如：女强人, 末日生存, 吐槽役, 异能者, 寻友之旅）。

**输出格式:**
你必须只返回一个标准的、不含任何额外注释或markdown标记的JSON对象，格式如下：
{{
  "description": "<你创作的详细描述>",
  "personality": "<你创作的深度性格分析>",
  "first_mes": "<你创作的第一句话>",
  "alternate_greetings": [
    "<备选开场白1>",
    "<备选开场白2>",
    "<备选开场白3>"
  ],
  "tags": [
    "<标签1>",
    "<标签2>",
    "<标签3>",
    "<标签4>",
    "<标签5>"
  ]
}}
"""

    async def generate_card_with_llm(self, role_file: Path, idx: int, total: int) -> None:
        """使用LLM处理单个角色文件"""
        char_name = role_file.stem
        print(f"[PROCESS] [{idx}/{total}] 开始处理角色: {char_name}")

        try:
            with open(role_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] [{idx}/{total}] 读取或解析 {role_file.name} 失败: {e}")
            return

        prompt = self.get_card_generation_prompt(raw_data)
        messages = [
            {"role": "system", "content": "你是一位专业的角色设定作家和SillyTavern角色卡制作专家。"},
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
                        response_format={"type": "json_object"} # 请求JSON输出
                    )
                    
                    llm_output = response.choices[0].message.content
                    refined_data = json.loads(llm_output)

                    # 构建最终的角色卡
                    final_card = {
                        "spec": "chara_card_v2",
                        "spec_version": "2.0",
                        "data": {
                            "name": raw_data.get("name", char_name),
                            "creator": raw_data.get("creator", "st_book"),
                            "character_version": raw_data.get("character_version", "1.1"),
                            "description": refined_data.get("description", ""),
                            "personality": refined_data.get("personality", ""),
                            "scenario": raw_data.get("scenario", ""), # 场景可以保留原始的
                            "first_mes": refined_data.get("first_mes", ""),
                            "mes_example": "",
                            "creator_notes": f"由st_book AI增强生成。原始条目数: {raw_data.get('entries', 1)}",
                            "system_prompt": "",
                            "post_history_instructions": "",
                            "alternate_greetings": refined_data.get("alternate_greetings", []),
                            "tags": refined_data.get("tags", []),
                            "extensions": {}
                        }
                    }

                    # 保存角色卡
                    card_file = self.cards_dir / f"{final_card['data']['name']}.json"
                    with open(card_file, 'w', encoding='utf-8') as f:
                        json.dump(final_card, f, ensure_ascii=False, indent=2)

                    print(f"[SUCCESS] [{idx}/{total}] 已创建高质量角色卡: {card_file.name}")
                    return # 成功后退出循环

                except Exception as e:
                    print(f"[WARNING] [{idx}/{total}] AI处理角色 {char_name} 失败 (尝试 {attempt + 1}/{self.retry_limit}): {e}")
                    if attempt < self.retry_limit - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        print(f"[ERROR] [{idx}/{total}] 角色 {char_name} 在达到最大重试次数后仍然失败。")

    async def create_all_cards_async(self):
        """异步创建所有角色卡"""
        print("="*60)
        print(f"开始使用 {self.pro_model} 智能生成 SillyTavern 角色卡...")
        print("="*60)

        if not self.roles_dir.exists():
            print(f"错误: 找不到角色数据目录 {self.roles_dir}")
            return

        role_files = list(self.roles_dir.glob("*.json"))
        if not role_files:
            print(f"在 {self.roles_dir} 中没有找到角色数据文件。")
            return
            
        print(f"找到 {len(role_files)} 个角色数据文件，准备进行AI增强处理。")

        tasks = [
            self.generate_card_with_llm(role_file, idx + 1, len(role_files))
            for idx, role_file in enumerate(role_files)
        ]
        await asyncio.gather(*tasks)

        print("\n高质量角色卡创建完成！")
        print(f"保存位置: {self.cards_dir}")

def main():
    """主函数"""
    creator = CardCreator()
    asyncio.run(creator.create_all_cards_async())

if __name__ == "__main__":
    main()
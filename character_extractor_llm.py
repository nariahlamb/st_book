#!/usr/bin/env python3
"""
LLM-based角色提取器 - 使用大语言模型智能分析角色信息
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
from project_config import get_config

class LLMCharacterExtractor:
    """使用LLM的智能角色提取器"""
    
    def __init__(self):
        self.config = get_config()
        # 从配置加载路径
        self.chunks_dir = Path(self.config.get("output.chunk_dir", "chunks"))
        self.output_dir = Path(self.config.get("output.character_responses_dir", "character_responses"))
        self.raw_dir = Path(self.config.get("output.character_responses_raw_dir", "character_responses_raw"))
        self.bad_dir = Path(self.config.get("output.character_responses_bad_dir", "character_responses_bad"))

        # 创建输出目录
        for dir_path in [self.output_dir, self.raw_dir, self.bad_dir]:
            dir_path.mkdir(exist_ok=True)

        # 初始化OpenAI客户端
        api_config = self.config.get_api_config()
        model_config = self.config.get_model_config()
        api_key = api_config.get("api_key")
        if not api_key:
            raise ValueError("❌ 找不到 API 金鑰，請在 config.yaml 中設定 'api.api_key'")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_config.get("api_base"),
            timeout=int(model_config.get("timeout", 300))
        )

        # 使用新的配置系统
        model_config = self.config.get_model_config()
        api_config = self.config.get_api_config()

        self.model = model_config.get("extraction_model", "gemini-2.5-flash")
        self.extraction_temperature = model_config.get("extraction_temperature", 0.3)
        self.max_tokens = int(model_config.get("max_tokens", 60000))

        # 性能配置
        self.max_concurrent = int(self.config.get("performance.max_concurrent", 1))
        self.retry_limit = int(self.config.get("performance.retry_limit", 5))
        self.retry_delay = int(self.config.get("performance.retry_delay", 10))
        self.rate_limit_delay = int(self.config.get("performance.rate_limit_delay", 5))
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 统计信息
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'total_characters': 0,
            'failed_chunks': 0
        }
    
    def get_character_analysis_prompt(self) -> str:
        """获取角色分析的提示词"""
        return self.config.get(
            "character_extraction_prompt",
            """你是一位专门分析小说角色的AI助手。请从以下小说段落中提取出现的所有角色信息。

要求：
1. 只提取真正的角色名称，不要提取普通词汇、代词或描述性词语
2. 对每个角色进行深度分析，包括外貌特征、性格特点、说话习惯、人际关系等
3. 如果同一个角色有多个称呼方式，请合并为一个条目
4. 输出格式必须是标准的JSON数组

输出格式示例：
[
  {
    "名字": "林三酒",
    "特徵": "黑发青年，身材修长，眼神锐利",
    "性格": "冷静理智，善于分析，有强烈的正义感",
    "說話習慣": "语调平静，用词精准，常用反问句",
    "備註": "主角，拥有特殊能力，与季山青关系密切"
  },
  {
    "名字": "季山青", 
    "特徵": "温和的外表，总是微笑",
    "性格": "表面温和实则深不可测，城府很深",
    "說話習慣": "说话温和有礼，但话中有话",
    "備註": "重要配角，身份神秘"
  }
]

请直接输出JSON数组，不要包含任何其他内容或markdown格式。

小说段落：
"""
        )
    
    async def process_single_chunk(self, chunk_file: Path, idx: int, total: int) -> Tuple[str, bool, int]:
        """处理单个文本块"""
        chunk_name = chunk_file.stem
        
        # 准备输出路径
        response_path = self.output_dir / f"{chunk_name}.json"
        raw_path = self.raw_dir / f"{chunk_name}.txt"
        bad_path = self.bad_dir / f"{chunk_name}.txt"
        
        # 如果已经处理过，跳过
        if response_path.exists():
            print(f"[SKIP] [{idx}/{total}] {chunk_name} 已存在，跳过")
            try:
                with open(response_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    return chunk_name, True, len(existing_data) if isinstance(existing_data, list) else 0
            except:
                pass
        
        # 读取文本块内容
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_text = f.read().strip()
        except Exception as e:
            print(f"[ERROR] [{idx}/{total}] 读取 {chunk_name} 失败：{e}")
            return chunk_name, False, 0
        
        if not chunk_text:
            print(f"[SKIP] [{idx}/{total}] {chunk_name} 内容为空")
            return chunk_name, True, 0
        
        # 并发控制
        async with self.semaphore:
            return await self._process_with_retry(
                chunk_name, chunk_text, response_path, raw_path, bad_path, idx, total
            )
    
    async def _process_with_retry(self, chunk_name: str, chunk_text: str, 
                                response_path: Path, raw_path: Path, bad_path: Path,
                                idx: int, total: int) -> Tuple[str, bool, int]:
        """带重试的处理逻辑"""
        prompt = self.get_character_analysis_prompt()
        
        messages = [
            {"role": "system", "content": "你是一位专业的小说角色分析AI助手。"},
            {"role": "user", "content": prompt + chunk_text}
        ]
        
        raw_output = None
        for attempt in range(1, self.retry_limit + 1):
            try:
                print(f"[PROCESS] [{idx}/{total}] 处理 {chunk_name}（第 {attempt} 次）")
                
                # API调用前等待，避免限流
                if attempt > 1:
                    await asyncio.sleep(self.rate_limit_delay)

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.extraction_temperature,
                    max_tokens=self.max_tokens
                )
                
                raw_output = getattr(response.choices[0].message, "content", None)
                if raw_output is None:
                    raise ValueError("API 回傳空內容")
                
                # 保存原始输出
                with open(raw_path, 'w', encoding='utf-8') as f:
                    f.write(raw_output)
                
                # 尝试解析JSON
                # 清理可能的markdown格式
                cleaned_output = raw_output.strip()
                if cleaned_output.startswith('```json'):
                    cleaned_output = cleaned_output[7:]
                if cleaned_output.endswith('```'):
                    cleaned_output = cleaned_output[:-3]
                cleaned_output = cleaned_output.strip()
                
                parsed_data = json.loads(cleaned_output)
                
                # 验证数据格式
                if not isinstance(parsed_data, list):
                    raise ValueError("输出不是JSON数组格式")
                
                # 过滤和验证角色数据
                valid_characters = []
                for char in parsed_data:
                    if isinstance(char, dict):
                        # 支持中文和英文字段名
                        name = None
                        if '名字' in char:
                            name = char['名字'].strip()
                        elif 'name' in char:
                            name = char['name'].strip()

                        if name and len(name) >= 2 and self._is_valid_character_name(name):
                            # 标准化字段名为中文（保持向后兼容）
                            standardized_char = self._standardize_character_fields(char)
                            valid_characters.append(standardized_char)
                
                # 保存处理后的数据
                with open(response_path, 'w', encoding='utf-8') as f:
                    json.dump(valid_characters, f, ensure_ascii=False, indent=2)
                
                char_count = len(valid_characters)
                print(f"[SUCCESS] [{idx}/{total}] {chunk_name} 处理成功，提取 {char_count} 个角色")
                return chunk_name, True, char_count
                
            except json.JSONDecodeError as e:
                with open(bad_path, 'w', encoding='utf-8') as f:
                    f.write(f"JSON解析错误: {e}\n\n原始输出:\n{raw_output or '[空回應]'}")
                print(f"[ERROR] [{idx}/{total}] JSON 格式錯誤：{chunk_name}")
                return chunk_name, False, 0
                
            except Exception as e:
                err_info = str(e)
                print(f"[WARNING] [{idx}/{total}] {chunk_name} 錯誤（第 {attempt} 次）：{err_info}")
                
                with open(bad_path, 'w', encoding='utf-8') as f:
                    f.write(f"处理错误: {err_info}\n\n原始输出:\n{raw_output or '[空回應]'}")
                
                if "rate limit" in err_info.lower() or "429" in err_info:
                    print(f"[WAIT] API 限流，等待 {self.retry_delay * attempt} 秒")
                    await asyncio.sleep(self.retry_delay * attempt)
                elif attempt < self.retry_limit:
                    await asyncio.sleep(self.retry_delay)
        
        print(f"[FAILED] [{idx}/{total}] 放棄 {chunk_name}，已達最大重試次數")
        return chunk_name, False, 0
    
    def _is_valid_character_name(self, name: str) -> bool:
        """验证是否为有效的角色名称"""
        # 从配置加载无效名称列表
        invalid_names = set(self.config.get("character_extraction.invalid_names", []))
        
        if name in invalid_names:
            return False
        
        # 排除纯数字或单字符
        if name.isdigit() or len(name) < 2:
            return False
        
        return True

    def _standardize_character_fields(self, char: Dict) -> Dict:
        """标准化角色字段名为中文格式"""
        # 字段映射：英文 -> 中文
        field_mapping = {
            'name': '名字',
            'aliases': '别名',
            'features': '特徵',
            'personality': '性格',
            'quote': '說話習慣',
            'motivation': '動機',
            'relationships': '人際關係',
            'notes': '備註'
        }

        standardized = {}

        # 转换已知字段
        for eng_field, chi_field in field_mapping.items():
            if eng_field in char:
                standardized[chi_field] = char[eng_field]

        # 保留已经是中文的字段
        for key, value in char.items():
            if key not in field_mapping and key not in standardized:
                standardized[key] = value

        # 确保必需字段存在
        if '名字' not in standardized and 'name' in char:
            standardized['名字'] = char['name']

        return standardized
    
    async def extract_all_characters(self):
        """提取所有文本块中的角色"""
        chunk_files = sorted(self.chunks_dir.glob("chunk_*.txt"))
        
        if not chunk_files:
            print(f"[ERROR] 在 {self.chunks_dir} 中找不到文本块文件")
            return
        
        self.stats['total_chunks'] = len(chunk_files)
        print(f"[START] 開始處理 {len(chunk_files)} 個文本块，最大並發數：{self.max_concurrent}")
        
        start_time = time.time()
        
        # 创建并发任务
        tasks = [
            self.process_single_chunk(chunk_file, idx + 1, len(chunk_files))
            for idx, chunk_file in enumerate(chunk_files)
        ]
        
        # 执行并发处理
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = 0
        total_characters = 0
        
        for result in results:
            if isinstance(result, Exception):
                self.stats['failed_chunks'] += 1
                print(f"[ERROR] 任务异常：{result}")
            elif isinstance(result, tuple) and len(result) == 3:
                chunk_name, success, char_count = result
                if success:
                    success_count += 1
                    total_characters += char_count
                else:
                    self.stats['failed_chunks'] += 1
        
        self.stats['processed_chunks'] = success_count
        self.stats['total_characters'] = total_characters
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"角色提取完成！")
        print(f"总共处理: {len(chunk_files)} 个文本块")
        print(f"成功处理: {success_count} 个")
        print(f"失败处理: {self.stats['failed_chunks']} 个")
        print(f"提取角色: {total_characters} 个")
        print(f"处理时间: {elapsed_time:.2f} 秒")
        print(f"平均速度: {elapsed_time/len(chunk_files):.2f} 秒/块")
        print(f"保存位置: {self.output_dir}")
        print(f"{'='*60}")

async def main():
    """主函数"""
    extractor = LLMCharacterExtractor()
    await extractor.extract_all_characters()

if __name__ == "__main__":
    asyncio.run(main())

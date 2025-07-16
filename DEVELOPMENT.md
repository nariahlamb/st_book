# 🛠️ 开发者快速参考 (Developer Quick Reference)

## 🚀 快速开始开发

### 环境设置
```bash
# 克隆项目
git clone <repository-url>
cd st_book

# 安装依赖
pip install -r requirements.txt

# 复制配置模板
cp config_template.yaml config.yaml
# 编辑config.yaml，填入你的API密钥
```

### 开发环境验证
```bash
# 验证配置加载
python -c "from project_config import get_config; print('Config loaded:', bool(get_config()))"

# 验证API连接
python -c "from project_config import get_config; print('API Key:', get_config().get('api.api_key')[:10] + '...')"

# 运行测试
python test_retry_mechanism.py
```

## 📁 项目结构速览

```
st_book/
├── 🎯 核心工作流
│   ├── character_workflow.py      # 主控制器
│   └── project_config.py          # 配置管理
├── 📝 文本处理
│   ├── text_splitter.py           # 文本分割
│   ├── character_extractor_llm.py # 角色提取
│   └── character_merger.py        # 角色合并
├── 🌍 世界书生成
│   ├── worldbook_extractor.py     # 世界观提取
│   ├── worldbook_generator.py     # 世界书生成
│   └── worldbook_parameter_optimizer.py # 参数优化
├── 🎭 角色卡生成
│   ├── create_card.py             # 角色卡生成
│   └── character_filter.py        # 角色筛选
├── 🧪 测试文件
│   ├── test_*.py                  # 各种测试
│   └── docs/                      # 文档
└── 📊 数据目录
    ├── chunks/                    # 文本分块
    ├── character_responses/       # 角色提取结果
    ├── wb_responses/             # 世界书提取结果
    ├── roles_json/               # 合并后角色
    ├── cards/                    # 最终角色卡
    └── worldbook/                # 最终世界书
```

## 🔧 常用开发命令

### 调试命令
```bash
# 查看当前状态
python character_workflow.py status

# 分步执行（调试用）
python character_workflow.py split
python character_workflow.py extract
python character_workflow.py merge

# 测试特定功能
python test_character_filter.py
python test_parallel_extraction.py
```

### 清理命令
```bash
# 清理中间文件
rm -rf chunks/ character_responses/ wb_responses/ roles_json/

# 清理输出文件
rm -rf cards/ worldbook/

# 清理测试文件
python test_character_filter.py cleanup
```

## 🏗️ 代码模式参考

### 1. 配置访问模式
```python
from project_config import get_config

class MyModule:
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.get("api.api_key")
        self.temperature = self.config.get("models.temperature", 0.3)
        self.retry_limit = int(self.config.get("performance.retry_limit", 3))
```

### 2. 异步LLM调用模式
```python
import asyncio
from openai import AsyncOpenAI

class LLMProcessor:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.retry_limit = 3
        self.retry_delay = 10
    
    async def call_llm_with_retry(self, messages):
        async with self.semaphore:
            for attempt in range(1, self.retry_limit + 1):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        await asyncio.sleep(self.retry_delay * attempt)
                    elif attempt < self.retry_limit:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        return "[]"  # fallback
```

### 3. 文件处理模式
```python
from pathlib import Path
import json

class FileProcessor:
    def __init__(self):
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def process_files(self):
        for file_path in self.input_dir.glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                result = self.process_content(content)
                
                output_file = self.output_dir / f"{file_path.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"处理 {file_path.name} 失败: {e}")
```

## 📋 命名规范速查

### Python命名
- **文件**: `snake_case.py`
- **类**: `PascalCase`
- **函数/变量**: `snake_case`
- **常量**: `UPPER_SNAKE_CASE`
- **私有方法**: `_private_method`

### 目录命名
- **数据目录**: `snake_case/`
- **输出目录**: 简洁名称 (`cards/`, `worldbook/`)

### 配置键命名
- **层级配置**: `section.key`
- **示例**: `api.api_key`, `models.temperature`

## 🧪 测试开发指南

### 创建新测试文件
```python
#!/usr/bin/env python3
"""
测试新功能的描述
"""

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试基本功能")
    # 测试代码
    return True

def test_error_handling():
    """测试错误处理"""
    print("🧪 测试错误处理")
    # 测试代码
    return True

def main():
    """主测试函数"""
    print("🔧 开始测试新功能")
    
    results = [
        test_basic_functionality(),
        test_error_handling()
    ]
    
    if all(results):
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    
    return all(results)

if __name__ == "__main__":
    main()
```

## 🔍 调试技巧

### 1. 配置调试
```python
# 检查配置加载
from project_config import get_config
config = get_config()
print(f"API Key: {config.get('api.api_key')[:10]}...")
print(f"Model: {config.get('models.extraction_model')}")
```

### 2. 日志调试
```python
# 添加详细日志
print(f"[DEBUG] 处理文件: {file_path}")
print(f"[DEBUG] 配置参数: {temperature}")
print(f"[DEBUG] 重试次数: {attempt}/{retry_limit}")
```

### 3. 异常调试
```python
try:
    result = await some_async_function()
except Exception as e:
    print(f"[ERROR] 详细错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
```

## 📊 性能优化建议

### 1. 并发优化
- 调整 `performance.max_concurrent`
- 监控API限流情况
- 使用 `asyncio.gather()` 并行处理

### 2. 内存优化
- 调整 `text_processing.max_chunk_chars`
- 及时清理大型变量
- 使用生成器处理大文件

### 3. API优化
- 合理设置重试参数
- 监控API调用成功率
- 使用缓存避免重复调用

## 🚨 常见问题解决

### API相关
- **429错误**: 检查限流设置，增加延迟
- **超时错误**: 增加timeout配置
- **认证错误**: 检查API密钥配置

### 文件相关
- **编码错误**: 确保使用UTF-8编码
- **路径错误**: 使用`Path`对象处理路径
- **权限错误**: 检查文件夹权限

### 内存相关
- **内存不足**: 减少chunk大小或并发数
- **处理缓慢**: 检查是否有内存泄漏

---

💡 **提示**: 开发时建议先在小数据集上测试，确认功能正常后再处理完整数据。

# 📋 命名规范 (Naming Convention)

## 🐍 Python代码命名规范

### 文件命名 (File Names)
```
✅ 正确示例:
character_extractor.py          # 模块文件
worldbook_generator.py          # 模块文件
test_character_filter.py        # 测试文件
config_validator.py             # 工具文件

❌ 错误示例:
CharacterExtractor.py           # 不使用PascalCase
character-extractor.py          # 不使用连字符
characterExtractor.py           # 不使用camelCase
```

### 类命名 (Class Names)
```python
✅ 正确示例:
class CharacterExtractor:       # PascalCase
class WorldbookGenerator:       # PascalCase
class ConfigManager:            # PascalCase

❌ 错误示例:
class character_extractor:      # 不使用snake_case
class worldbook_generator:      # 不使用snake_case
class configManager:            # 不使用camelCase
```

### 函数和方法命名 (Function/Method Names)
```python
✅ 正确示例:
def extract_characters():       # snake_case
def generate_worldbook():       # snake_case
def process_text_chunk():       # snake_case
def _private_method():          # 私有方法前缀下划线

❌ 错误示例:
def ExtractCharacters():        # 不使用PascalCase
def generateWorldbook():        # 不使用camelCase
def process-text-chunk():       # 不使用连字符
```

### 变量命名 (Variable Names)
```python
✅ 正确示例:
chunk_size = 1000              # snake_case
api_key = "your_key"           # snake_case
character_list = []            # snake_case
is_processing = True           # 布尔值使用is_前缀

❌ 错误示例:
ChunkSize = 1000               # 不使用PascalCase
apiKey = "your_key"            # 不使用camelCase
character-list = []            # 不使用连字符
```

### 常量命名 (Constants)
```python
✅ 正确示例:
DEFAULT_CHUNK_SIZE = 1000      # UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3         # UPPER_SNAKE_CASE
API_TIMEOUT = 300              # UPPER_SNAKE_CASE

❌ 错误示例:
default_chunk_size = 1000      # 不使用小写
DefaultChunkSize = 1000        # 不使用PascalCase
MAX-RETRY-ATTEMPTS = 3         # 不使用连字符
```

## 📁 目录和文件结构命名

### 目录命名 (Directory Names)
```
✅ 正确示例:
character_responses/           # snake_case，描述性
wb_responses/                  # 简洁缩写
character_responses_raw/       # 带状态后缀
character_responses_bad/       # 带状态后缀

❌ 错误示例:
CharacterResponses/            # 不使用PascalCase
character-responses/           # 不使用连字符
characterResponses/            # 不使用camelCase
```

### 数据文件命名 (Data File Names)
```
✅ 正确示例:
chunk_001.txt                  # 编号格式统一
chunk_001.json                 # 对应的JSON文件
mapping.json                   # 描述性名称
config.yaml                    # 配置文件
config_template.yaml           # 模板文件

❌ 错误示例:
chunk1.txt                     # 编号不统一
Chunk_001.txt                  # 不使用PascalCase
chunk-001.txt                  # 不使用连字符
```

### 输出文件命名 (Output File Names)
```
✅ 正确示例:
worldbook_st_v2.json          # 版本标识清晰
layered_worldbook.json         # 功能描述清晰
character_card.json            # 类型明确

❌ 错误示例:
worldbook.json                 # 版本不明确
WorldbookStV2.json            # 不使用PascalCase
worldbook-st-v2.json          # 不使用连字符
```

## ⚙️ 配置键命名规范

### 层级配置 (Hierarchical Config)
```yaml
✅ 正确示例:
api:
  api_key: "your_key"          # snake_case
  api_base: "https://..."      # snake_case
  
models:
  extraction_model: "gpt-4"    # snake_case
  extraction_temperature: 0.3  # snake_case
  
performance:
  max_concurrent: 1            # snake_case
  retry_limit: 3               # snake_case

❌ 错误示例:
API:                           # 不使用大写
  ApiKey: "your_key"           # 不使用PascalCase
  api-base: "https://..."      # 不使用连字符
  
Models:                        # 不使用PascalCase
  extractionModel: "gpt-4"     # 不使用camelCase
```

### 配置访问模式 (Config Access Pattern)
```python
✅ 正确示例:
config.get("api.api_key")              # 点记法
config.get("models.extraction_model")   # 点记法
config.get("performance.retry_limit", 3) # 带默认值

❌ 错误示例:
config.get("API.API_KEY")              # 不使用大写
config.get("models/extraction_model")   # 不使用斜杠
config.get("performance-retry-limit")   # 不使用连字符
```

## 🏷️ 特殊命名约定

### 测试文件命名 (Test File Names)
```
✅ 正确示例:
test_character_filter.py       # test_前缀
test_retry_mechanism.py        # test_前缀
test_parallel_extraction.py    # test_前缀

❌ 错误示例:
character_filter_test.py       # 后缀不规范
TestCharacterFilter.py         # 不使用PascalCase
character_filter.test.py       # 不使用点分隔
```

### 临时和备份文件 (Temporary/Backup Files)
```
✅ 正确示例:
roles_json/filtered_out/       # 状态目录
character_responses_bad/       # 错误文件目录
character_responses_raw/       # 原始文件目录
*.tmp                          # 临时文件扩展名

❌ 错误示例:
roles_json/FilteredOut/        # 不使用PascalCase
character_responses.bad/       # 不使用点分隔目录
character-responses-raw/       # 不使用连字符
```

### 日志和状态标识 (Log/Status Identifiers)
```python
✅ 正确示例:
print(f"[SUCCESS] 操作完成")     # 大写状态标识
print(f"[ERROR] 处理失败")       # 大写状态标识
print(f"[WARNING] 警告信息")     # 大写状态标识
print(f"[DEBUG] 调试信息")       # 大写状态标识

❌ 错误示例:
print(f"[success] 操作完成")     # 不使用小写
print(f"[Error] 处理失败")       # 不使用混合大小写
print(f"[WARN] 警告信息")        # 缩写不一致
```

## 📊 数据结构命名

### JSON字段命名 (JSON Field Names)
```json
✅ 正确示例:
{
  "character_name": "张三",      // snake_case
  "character_description": "...", // snake_case
  "event_summary": "事件摘要",    // snake_case
  "rule_type": "魔法体系"         // snake_case
}

❌ 错误示例:
{
  "CharacterName": "张三",        // 不使用PascalCase
  "characterDescription": "...",  // 不使用camelCase
  "event-summary": "事件摘要",    // 不使用连字符
  "RuleType": "魔法体系"          // 不使用PascalCase
}
```

### 数据库/集合命名 (Database/Collection Names)
```python
✅ 正确示例:
characters_collection          # snake_case
worldbook_entries             # snake_case
extraction_results            # snake_case

❌ 错误示例:
CharactersCollection          # 不使用PascalCase
worldbookEntries             # 不使用camelCase
extraction-results           # 不使用连字符
```

## 🔍 命名检查清单

### 代码审查检查项
- [ ] 文件名使用snake_case
- [ ] 类名使用PascalCase
- [ ] 函数/变量名使用snake_case
- [ ] 常量使用UPPER_SNAKE_CASE
- [ ] 配置键使用snake_case和点记法
- [ ] 目录名使用snake_case
- [ ] 测试文件使用test_前缀
- [ ] 私有方法使用_前缀
- [ ] 布尔变量使用is_/has_前缀
- [ ] JSON字段使用snake_case

### 命名质量标准
- **描述性**: 名称应该清楚表达用途
- **一致性**: 同类型的命名保持一致
- **简洁性**: 避免过长的名称
- **可读性**: 易于理解和记忆
- **无歧义**: 避免可能引起混淆的名称

## 📝 命名示例对照表

| 类型 | 正确示例 | 错误示例 | 说明 |
|------|----------|----------|------|
| 模块文件 | `character_extractor.py` | `CharacterExtractor.py` | 使用snake_case |
| 类名 | `CharacterExtractor` | `character_extractor` | 使用PascalCase |
| 函数名 | `extract_characters()` | `ExtractCharacters()` | 使用snake_case |
| 变量名 | `chunk_size` | `ChunkSize` | 使用snake_case |
| 常量 | `MAX_RETRY_ATTEMPTS` | `max_retry_attempts` | 使用UPPER_SNAKE_CASE |
| 配置键 | `api.api_key` | `API.API_KEY` | 使用snake_case和点记法 |
| 目录名 | `character_responses/` | `CharacterResponses/` | 使用snake_case |
| 测试文件 | `test_character_filter.py` | `character_filter_test.py` | 使用test_前缀 |

---

💡 **提示**: 遵循一致的命名规范有助于提高代码可读性和维护性，建议在代码审查时严格检查命名规范。

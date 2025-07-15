✨ AI驱动的小说角色卡与世界书生成器

🔍 **项目简介**
一个基于大语言模型（LLM）的自动化工具，智能提取中文小说文本中的角色信息和世界观设定，自动生成符合SillyTavern格式的高质量角色卡和结构化世界书。

🌟 **项目特点**
🔹 **高度自动化**: 一键式命令，全程无需人工干预
🔹 **两阶段处理**: "先提取，后升华"的智能工作流，保证最终产出质量
🔹 **高度可定制**: 通过config.yaml灵活配置AI行为
🔹 **模块化设计**: 代码结构清晰，易于维护和扩展

📁 **目录结构**
```
st_book/
├───character_extractor_llm.py  # 角色信息提取器
├───character_merger.py         # 角色信息合并器
├───character_workflow.py       # 主工作流管理器 (你的主要入口)
├───config_template.yaml        # 配置文件模板
├───create_card.py              # AI增强的角色卡生成器
├───project_config.py           # 项目配置加载器
├───README.md                   # 本文档
├───text_splitter.py            # 文本分割器
├───worldbook_extractor.py      # 世界书条目提取器
├───worldbook_generator.py      # AI增强的世界书生成器
├───cards/                      # 【输出】最终生成的SillyTavern角色卡
├───chunks/                     # (中间) 小说文本分块
├───character_responses/        # (中间) 提取的原始角色信息
├───roles_json/                # (中间) 合并后的原始角色档案
├───wb_responses/              # (中间) 提取的原始世界书条目
└───worldbook/                 # 【输出】最终生成的结构化世界书
```

🚀 **快速开始**

1️⃣ **环境准备**
```bash
git clone https://github.com/nariahlamb/st_book.git
cd st_book
pip install -r requirements.txt
```

2️⃣ **配置设置**
```bash
cp config_template.yaml config.yaml
```

🔧 **配置示例**
```yaml
api:
  api_key: "YOUR_API_KEY_HERE"
  api_base: "https://api.openai.com/v1"
```

3️⃣ **执行命令**

🔹 **角色卡生成**:
```bash
python character_workflow.py auto
```

🔹 **世界书生成**:
```bash
python character_workflow.py wb-auto
```

📚 **核心模块说明**

🔹 **主要组件**:
- character_workflow.py: 主控制脚本
- config.yaml: 项目配置中心

🔹 **角色卡生成流程**:
1. text_splitter.py: 文本分割
2. character_extractor_llm.py: AI提取角色信息
3. character_merger.py: 信息合并
4. character_filter.py: 角色筛选
5. create_card.py: 高质量角色卡生成

🔹 **世界书生成流程**:
1. worldbook_extractor.py: 提取世界观设定
2. worldbook_generator.py: 生成结构化世界书

🛠️ **高级使用说明**

🔹 **分步执行命令**:
```bash
# 角色卡制作
python character_workflow.py split      # 分割文本
python character_workflow.py extract    # 提取角色
python character_workflow.py merge      # 合并角色
python character_workflow.py filter     # 筛选角色
python character_workflow.py create     # 生成角色卡

# 世界书制作
python character_workflow.py wb-extract    # 提取世界书条目
python character_workflow.py wb-generate   # 生成结构化世界书

# 工具命令
python character_workflow.py status     # 查看当前进度
python character_workflow.py help       # 查看帮助信息
```

⚙️ **配置说明**

🔹 **核心配置项**:
- API配置: api.api_key 和 api.api_base
- 模型选择: models.extraction_model 和 models.generation_model
- 温度参数: AI创作随机性控制
- 角色筛选: character_filter.keep_count

🔹 **输出目录**:
- cards/ - 最终角色卡文件
- worldbook/ - 最终世界书文件
- roles_json/ - 中间角色数据
- chunks/ - 分割文本块

❗ **故障排除**
1. API调用失败: 检查API密钥和网络连接
2. 角色提取为空: 检查小说文本格式和编码
3. 内存不足: 调整text_processing.max_chunk_chars参数
4. 生成速度慢: 调整performance.max_concurrent参数

🤝 **贡献**
欢迎提交Issue和Pull Request来改进项目！

📄 **许可证**
本项目采用MIT许可证。

#!/usr/bin/env python3
"""
项目配置文件 - 统一配置管理
支持新的配置文件结构，提供向后兼容性
"""

import json
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

class ProjectConfig:
    """项目配置管理 - 支持新的统一配置结构"""

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件 - 支持新的统一配置结构"""
        config_path = Path(self.config_file)

        if not config_path.exists():
            print(f"警告: 配置文件 {self.config_file} 不存在，使用默认配置")
            return self._get_default_config()

        try:
            if YAML_AVAILABLE:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f) or {}
            else:
                print("警告: 未安装yaml库，无法读取配置文件")
                return self._get_default_config()

            # 验证并转换配置结构
            return self._normalize_config(loaded_config)

        except Exception as e:
            print(f"警告: 配置文件加载失败，使用默认配置: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（向后兼容）"""
        return {
            # 保持向后兼容的基本配置
            "api_key": "",
            "api_base": "",
            "model": "gemini-2.5-flash",
            "pro_model": "gemini-2.5-pro",
            "max_chunk_chars": 30000,
            "buffer_chars": 200,
            "max_concurrent": 1,
            "retry_limit": 5,
            "retry_delay": 10,
            "rate_limit_delay": 5,
            # 新的配置结构
            "input": {"source_file": "a.txt", "encoding": "utf-8"},
            "output": {
                "chunk_dir": "chunks",
                "character_responses_dir": "character_responses",
                "roles_json_dir": "roles_json",
                "cards_dir": "cards",
                "worldbook_dir": "worldbook"
            },
            "models": {
                "extraction_model": "gemini-2.5-flash",
                "generation_model": "gemini-2.5-pro",
                "extraction_temperature": 0.3,
                "generation_temperature": 0.2,
                "max_tokens": 60000,
                "timeout": 300
            },
            "similarity": {
                "name_threshold": 0.85,
                "content_threshold": 0.8,
                "merge_threshold": 0.7
            },
            "validation": {
                "min_character_name_length": 2,
                "min_content_length": 20,
                "max_entries": 2000
            }
        }

    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """标准化配置结构，确保向后兼容性"""
        # 如果是新的配置结构，直接返回
        if 'api' in config and 'models' in config:
            return config

        # 如果是旧的配置结构，进行转换
        normalized = self._get_default_config()

        # 转换旧的配置项到新结构
        if 'api_key' in config:
            normalized['api'] = {
                'api_key': config.get('api_key', ''),
                'api_base': config.get('api_base', '')
            }

        if 'model' in config or 'pro_model' in config:
            normalized['models'].update({
                'extraction_model': config.get('model', 'gemini-2.5-flash'),
                'generation_model': config.get('pro_model', 'gemini-2.5-pro')
            })

        # 保持其他配置项
        for key, value in config.items():
            if key not in ['api_key', 'api_base', 'model', 'pro_model']:
                normalized[key] = value

        return normalized

    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_api_config(self) -> Dict[str, str]:
        """获取API配置"""
        # 支持新旧配置结构
        if 'api' in self.config:
            return self.config['api']
        else:
            return {
                'api_key': self.config.get('api_key', ''),
                'api_base': self.config.get('api_base', '')
            }

    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        # 支持新旧配置结构
        if 'models' in self.config:
            return self.config['models']
        else:
            return {
                'extraction_model': self.config.get('model', 'gemini-2.5-flash'),
                'generation_model': self.config.get('pro_model', 'gemini-2.5-pro'),
                'extraction_temperature': 0.3,
                'generation_temperature': 0.2,
                'max_tokens': 60000,
                'timeout': 300
            }


# 全局配置实例
_global_config = None

def get_config() -> ProjectConfig:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = ProjectConfig()
    return _global_config

def reload_config():
    """重新加载配置"""
    global _global_config
    _global_config = ProjectConfig()

    def load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            print("警告: 未安装yaml库，使用默认配置")
            return {}
        except Exception as e:
            print(f"警告: YAML解析失败: {e}")
            return {}

        # 默认配置（如果config.yaml不存在）
        default_config = {
            "project": {
                "name": "testbook",
                "title": "测试世界书",
                "description": "基于AI智能优化生成的高质量世界书",
                "author": "AI智能优化生成",
                "version": "1.0"
            },
            "worldbook": {
                "name_template": "{title}-高质量世界书",
                "filename_template": "{name}-高质量世界书.json",
                "world_reference": "{title}世界",
                "concept_reference": "{title}世界观中的重要概念"
            },
            "paths": {
                "input_file": "mrly.txt",
                "chunk_output_dir": "chunks",
                "character_responses_dir": "character_responses",
                "roles_json_dir": "roles_json",
                "cards_dir": "cards",
                "worldbook_dir": "worldbook",
                "cache_dir": "cache",
                "logs_dir": "logs"
            },
            "text_splitting": {
                "max_chunk_chars": 30000,
                "buffer_chars": 200,
                "chapter_patterns": [
                    "第[一二三四五六七八九十百千万\\d]+章",
                    "第[一二三四五六七八九十百千万\\d]+节",
                    "第[一二三四五六七八九十百千万\\d]+回"
                ]
            },
            "character_extraction": {
                "similarity_threshold": 0.7,
                "merge_similar_names": True,
                "max_features_per_character": 5,
                "max_dialogues_per_character": 3
            },
            "processing": {
                "similarity_threshold_name": 0.95,
                "similarity_threshold_content": 0.85,
                "min_content_length": 20,
                "max_entries": 2000
            }
        }
        
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                # 合并配置
                self._merge_config(default_config, loaded_config)
            except ImportError:
                print("警告: 未安装yaml库，使用默认配置")
            except Exception as e:
                print(f"警告: 配置文件加载失败，使用默认配置: {e}")
        
        return default_config
    
    def _merge_config(self, default: dict, loaded: dict):
        """递归合并配置"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value
    
    def get(self, key_path: str, default=None):
        """获取配置值，支持点号路径"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_project_name(self) -> str:
        """获取项目名称"""
        return str(self.get('project.name', 'testbook'))

    def get_project_title(self) -> str:
        """获取项目标题"""
        return str(self.get('project.title', '测试世界书'))
    
    def get_worldbook_name(self) -> str:
        """获取世界书名称"""
        template = str(self.get('worldbook.name_template', '{title}-高质量世界书'))
        return template.format(
            name=self.get_project_name(),
            title=self.get_project_title()
        )

    def get_worldbook_filename(self) -> str:
        """获取世界书文件名"""
        template = str(self.get('worldbook.filename_template', '{name}-高质量世界书.json'))
        return template.format(
            name=self.get_project_name(),
            title=self.get_project_title()
        )

    def get_world_reference(self) -> str:
        """获取世界引用名称"""
        template = str(self.get('worldbook.world_reference', '{title}世界'))
        return template.format(
            name=self.get_project_name(),
            title=self.get_project_title()
        )

    def get_concept_reference(self) -> str:
        """获取概念引用名称"""
        template = str(self.get('worldbook.concept_reference', '{title}世界观中的重要概念'))
        return template.format(
            name=self.get_project_name(),
            title=self.get_project_title()
        )
    
    def save_config(self):
        """保存配置到文件"""
        try:
            import yaml
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            # 如果没有yaml，保存为JSON
            json_file = self.config_file.replace('.yaml', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

# 全局配置实例
config = ProjectConfig()

def get_config() -> ProjectConfig:
    """获取全局配置实例"""
    return config

if __name__ == "__main__":
    # 测试新的配置系统
    cfg = get_config()
    print("=== 配置系统测试 ===")
    print(f"API配置: {cfg.get_api_config()}")
    print(f"模型配置: {cfg.get_model_config()}")
    print(f"输入文件: {cfg.get('input.source_file', 'a.txt')}")
    print(f"相似度阈值: {cfg.get('similarity.name_threshold', 0.85)}")
    print("配置系统测试完成")

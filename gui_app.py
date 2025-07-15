import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import yaml
import subprocess
import os

CONFIG_PATH = "config.yaml"
WORKFLOW_SCRIPT = "character_workflow.py"

class STBookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ST Book GUI")
        self.root.geometry("1000x800")

        self.config_data = {}
        self.create_widgets()
        self.load_config(CONFIG_PATH) # Load default config on startup

    def create_widgets(self):
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Config Tab
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="配置")
        self.create_config_tab(self.config_frame)

        # Workflow Tab
        self.workflow_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.workflow_frame, text="工作流")
        self.create_workflow_tab(self.workflow_frame)

        # Log Area
        self.log_frame = ttk.LabelFrame(self.root, text="日志输出")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, height=15, state='disabled')
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def create_config_tab(self, parent_frame):
        # Use a canvas with a scrollbar for the config tab
        canvas = tk.Canvas(parent_frame)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Load Config Button ---
        load_config_button = ttk.Button(self.scrollable_frame, text="导入 Config.yaml", command=self.browse_config_file)
        load_config_button.pack(pady=5)

        # API Configuration
        api_frame = ttk.LabelFrame(self.scrollable_frame, text="API 配置")
        api_frame.pack(padx=10, pady=5, fill="x")

        self.api_entries = {}
        api_fields = ["api_key", "api_base", "model", "pro_model"]
        for i, field in enumerate(api_fields):
            ttk.Label(api_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(api_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.api_entries[field] = entry
        api_frame.grid_columnconfigure(1, weight=1)

        # Input/Output Directories
        io_frame = ttk.LabelFrame(self.scrollable_frame, text="输入/输出目录")
        io_frame.pack(padx=10, pady=5, fill="x")

        self.io_entries = {}
        io_fields = [
            "input_file", "chunk_output_dir", "mapping_file",
            "response_output_dir", "raw_output_dir", "bad_output_dir",
            "role_json_dir", "character_stats_file",
            "card_output_dir", "worldbook_output_dir"
        ]
        for i, field in enumerate(io_fields):
            ttk.Label(io_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(io_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.io_entries[field] = entry
            if field == "input_file": # Add browse button for input_file
                browse_button = ttk.Button(io_frame, text="浏览", command=self.browse_input_file)
                browse_button.grid(row=i, column=2, padx=5, pady=2)
        io_frame.grid_columnconfigure(1, weight=1)


        # Text Splitting Configuration
        text_split_frame = ttk.LabelFrame(self.scrollable_frame, text="文本分割配置")
        text_split_frame.pack(padx=10, pady=5, fill="x")

        self.text_split_entries = {}
        text_split_fields = ["max_chunk_chars", "buffer_chars"]
        for i, field in enumerate(text_split_fields):
            ttk.Label(text_split_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(text_split_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.text_split_entries[field] = entry
        text_split_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(text_split_frame, text="chapter_patterns (每行一个):").grid(row=len(text_split_fields), column=0, padx=5, pady=2, sticky="nw")
        self.chapter_patterns_text = scrolledtext.ScrolledText(text_split_frame, wrap=tk.WORD, height=5, width=50)
        self.chapter_patterns_text.grid(row=len(text_split_fields), column=1, padx=5, pady=2, sticky="ew")
        text_split_frame.grid_rowconfigure(len(text_split_fields), weight=1)


        # Performance Optimization Configuration
        perf_opt_frame = ttk.LabelFrame(self.scrollable_frame, text="性能优化配置")
        perf_opt_frame.pack(padx=10, pady=5, fill="x")

        self.perf_opt_entries = {}
        perf_opt_fields = ["max_concurrent", "retry_limit", "retry_delay", "max_test_chunks", "rate_limit_delay", "batch_size"]
        for i, field in enumerate(perf_opt_fields):
            ttk.Label(perf_opt_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(perf_opt_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.perf_opt_entries[field] = entry

        self.test_mode_var = tk.BooleanVar()
        ttk.Checkbutton(perf_opt_frame, text="test_mode", variable=self.test_mode_var).grid(row=len(perf_opt_fields), column=0, columnspan=2, padx=5, pady=2, sticky="w")

        self.enable_cache_var = tk.BooleanVar()
        ttk.Checkbutton(perf_opt_frame, text="enable_cache", variable=self.enable_cache_var).grid(row=len(perf_opt_fields)+1, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        ttk.Label(perf_opt_frame, text="cache_dir:").grid(row=len(perf_opt_fields)+2, column=0, padx=5, pady=2, sticky="w")
        self.cache_dir_entry = ttk.Entry(perf_opt_frame, width=50)
        self.cache_dir_entry.grid(row=len(perf_opt_fields)+2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(perf_opt_frame, text="cache_expiry_days:").grid(row=len(perf_opt_fields)+3, column=0, padx=5, pady=2, sticky="w")
        self.cache_expiry_days_entry = ttk.Entry(perf_opt_frame, width=50)
        self.cache_expiry_days_entry.grid(row=len(perf_opt_fields)+3, column=1, padx=5, pady=2, sticky="ew")

        perf_opt_frame.grid_columnconfigure(1, weight=1)

        # Character Analysis Configuration
        char_analysis_frame = ttk.LabelFrame(self.scrollable_frame, text="角色分析配置")
        char_analysis_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(char_analysis_frame, text="character_extraction_prompt:声:").grid(row=0, column=0, padx=5, pady=2, sticky="nw")
        self.char_extraction_prompt_text = scrolledtext.ScrolledText(char_analysis_frame, wrap=tk.WORD, height=10, width=50)
        self.char_extraction_prompt_text.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        char_analysis_frame.grid_columnconfigure(1, weight=1)
        char_analysis_frame.grid_rowconfigure(0, weight=1)

        # Name Normalization
        name_norm_frame = ttk.LabelFrame(char_analysis_frame, text="名称标准化")
        name_norm_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.name_norm_enable_var = tk.BooleanVar()
        ttk.Checkbutton(name_norm_frame, text="enable", variable=self.name_norm_enable_var).grid(row=0, column=0, padx=5, pady=2, sticky="w")

        ttk.Label(name_norm_frame, text="similarity_threshold:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.similarity_threshold_entry = ttk.Entry(name_norm_frame, width=50)
        self.similarity_threshold_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        self.merge_similar_names_var = tk.BooleanVar()
        ttk.Checkbutton(name_norm_frame, text="merge_similar_names", variable=self.merge_similar_names_var).grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        name_norm_frame.grid_columnconfigure(1, weight=1)

        # Worldbook Configuration
        wb_frame = ttk.LabelFrame(self.scrollable_frame, text="世界书配置")
        wb_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(wb_frame, text="worldbook_extraction_prompt:").grid(row=0, column=0, padx=5, pady=2, sticky="nw")
        self.wb_extraction_prompt_text = scrolledtext.ScrolledText(wb_frame, wrap=tk.WORD, height=10, width=50)
        self.wb_extraction_prompt_text.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        wb_frame.grid_columnconfigure(1, weight=1)
        wb_frame.grid_rowconfigure(0, weight=1)

        # SillyTavern Worldbook Configuration
        st_wb_frame = ttk.LabelFrame(wb_frame, text="SillyTavern世界书配置")
        st_wb_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.st_wb_entries = {}
        st_wb_fields = ["name", "description", "scan_depth", "token_budget"]
        for i, field in enumerate(st_wb_fields):
            ttk.Label(st_wb_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(st_wb_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.st_wb_entries[field] = entry

        self.recursive_scanning_var = tk.BooleanVar()
        ttk.Checkbutton(st_wb_frame, text="recursive_scanning", variable=self.recursive_scanning_var).grid(row=len(st_wb_fields), column=0, columnspan=2, padx=5, pady=2, sticky="w")

        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(st_wb_frame, text="case_sensitive", variable=self.case_sensitive_var).grid(row=len(st_wb_fields)+1, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        self.match_whole_words_var = tk.BooleanVar()
        ttk.Checkbutton(st_wb_frame, text="match_whole_words", variable=self.match_whole_words_var).grid(row=len(st_wb_fields)+2, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        st_wb_frame.grid_columnconfigure(1, weight=1)

        # Default Entry Settings
        default_entry_frame = ttk.LabelFrame(st_wb_frame, text="条目默认设置")
        default_entry_frame.grid(row=len(st_wb_fields)+3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.default_entry_entries = {}
        default_entry_fields = ["order", "position", "probability", "depth"]
        for i, field in enumerate(default_entry_fields):
            ttk.Label(default_entry_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(default_entry_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.default_entry_entries[field] = entry

        self.default_entry_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(default_entry_frame, text="enabled", variable=self.default_entry_enabled_var).grid(row=len(default_entry_fields), column=0, columnspan=2, padx=5, pady=2, sticky="w")
        default_entry_frame.grid_columnconfigure(1, weight=1)

        # Character Card Enhancement Configuration
        char_card_frame = ttk.LabelFrame(self.scrollable_frame, text="角色卡增强配置")
        char_card_frame.pack(padx=10, pady=5, fill="x")

        self.char_card_vars = {}
        char_card_checkboxes = ["generate_mes_example", "generate_alternate_greetings", "generate_system_prompt", "extract_tags"]
        for i, field in enumerate(char_card_checkboxes):
            var = tk.BooleanVar()
            ttk.Checkbutton(char_card_frame, text=field, variable=var).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.char_card_vars[field] = var

        ttk.Label(char_card_frame, text="alternate_greetings_count:").grid(row=len(char_card_checkboxes), column=0, padx=5, pady=2, sticky="w")
        self.alternate_greetings_count_entry = ttk.Entry(char_card_frame, width=50)
        self.alternate_greetings_count_entry.grid(row=len(char_card_checkboxes), column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(char_card_frame, text="max_tags:").grid(row=len(char_card_checkboxes)+1, column=0, padx=5, pady=2, sticky="w")
        self.max_tags_entry = ttk.Entry(char_card_frame, width=50)
        self.max_tags_entry.grid(row=len(char_card_checkboxes)+1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(char_card_frame, text="creator:").grid(row=len(char_card_checkboxes)+2, column=0, padx=5, pady=2, sticky="w")
        self.creator_entry = ttk.Entry(char_card_frame, width=50)
        self.creator_entry.grid(row=len(char_card_checkboxes)+2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(char_card_frame, text="character_version:").grid(row=len(char_card_checkboxes)+3, column=0, padx=5, pady=2, sticky="w")
        self.character_version_entry = ttk.Entry(char_card_frame, width=50)
        self.character_version_entry.grid(row=len(char_card_checkboxes)+3, column=1, padx=5, pady=2, sticky="ew")
        char_card_frame.grid_columnconfigure(1, weight=1)

        # Log Configuration
        log_frame = ttk.LabelFrame(self.scrollable_frame, text="日志配置")
        log_frame.pack(padx=10, pady=5, fill="x")

        self.log_entries = {}
        log_fields = ["log_file", "log_level", "log_format"]
        for i, field in enumerate(log_fields):
            ttk.Label(log_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(log_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.log_entries[field] = entry

        self.verbose_logging_var = tk.BooleanVar()
        ttk.Checkbutton(log_frame, text="verbose_logging", variable=self.verbose_logging_var).grid(row=len(log_fields), column=0, columnspan=2, padx=5, pady=2, sticky="w")
        log_frame.grid_columnconfigure(1, weight=1)

        # Advanced Configuration
        adv_frame = ttk.LabelFrame(self.scrollable_frame, text="高级配置")
        adv_frame.pack(padx=10, pady=5, fill="x")

        # Model Parameters
        model_params_frame = ttk.LabelFrame(adv_frame, text="模型参数")
        model_params_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.model_params_entries = {}
        model_params_fields = ["temperature", "max_tokens", "timeout"]
        for i, field in enumerate(model_params_fields):
            ttk.Label(model_params_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(model_params_frame, width=50)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.model_params_entries[field] = entry
        model_params_frame.grid_columnconfigure(1, weight=1)

        # Error Handling
        error_handling_frame = ttk.LabelFrame(adv_frame, text="错误处理")
        error_handling_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.continue_on_error_var = tk.BooleanVar()
        ttk.Checkbutton(error_handling_frame, text="continue_on_error", variable=self.continue_on_error_var).grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.save_error_details_var = tk.BooleanVar()
        ttk.Checkbutton(error_handling_frame, text="save_error_details", variable=self.save_error_details_var).grid(row=1, column=0, padx=5, pady=2, sticky="w")

        ttk.Label(error_handling_frame, text="max_consecutive_errors:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.max_consecutive_errors_entry = ttk.Entry(error_handling_frame, width=50)
        self.max_consecutive_errors_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        error_handling_frame.grid_columnconfigure(1, weight=1)

        # Output Format
        output_format_frame = ttk.LabelFrame(adv_frame, text="输出格式")
        output_format_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.ensure_ascii_var = tk.BooleanVar()
        ttk.Checkbutton(output_format_frame, text="ensure_ascii", variable=self.ensure_ascii_var).grid(row=0, column=0, padx=5, pady=2, sticky="w")

        ttk.Label(output_format_frame, text="indent:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.indent_entry = ttk.Entry(output_format_frame, width=50)
        self.indent_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        self.sort_keys_var = tk.BooleanVar()
        ttk.Checkbutton(output_format_frame, text="sort_keys", variable=self.sort_keys_var).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        output_format_frame.grid_columnconfigure(1, weight=1)

        # Experimental Features
        exp_frame = ttk.LabelFrame(self.scrollable_frame, text="实验性功能")
        exp_frame.pack(padx=10, pady=5, fill="x")

        self.exp_vars = {}
        exp_checkboxes = ["enable_batch_processing", "enable_smart_chunking", "enable_character_relationships"]
        for i, field in enumerate(exp_checkboxes):
            var = tk.BooleanVar()
            ttk.Checkbutton(exp_frame, text=field, variable=var).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.exp_vars[field] = var
        exp_frame.grid_columnconfigure(0, weight=1)


        # Save Button
        save_button = ttk.Button(self.scrollable_frame, text="保存配置", command=self.save_config)
        save_button.pack(pady=10)

    def create_workflow_tab(self, parent_frame):
        # Auto Commands
        auto_frame = ttk.LabelFrame(parent_frame, text="一键自动化命令")
        auto_frame.pack(padx=10, pady=5, fill="x")

        ttk.Button(auto_frame, text="生成角色卡 (auto)", command=lambda: self.run_workflow("auto")).pack(pady=5, fill="x")
        ttk.Button(auto_frame, text="生成世界书 (wb-auto)", command=lambda: self.run_workflow("wb-auto")).pack(pady=5, fill="x")

        # Step-by-step Commands (Character Card)
        char_step_frame = ttk.LabelFrame(parent_frame, text="角色卡分步流程")
        char_step_frame.pack(padx=10, pady=5, fill="x")

        ttk.Button(char_step_frame, text="分割文本 (split)", command=lambda: self.run_workflow("split")).pack(pady=5, fill="x")
        ttk.Button(char_step_frame, text="提取角色信息 (extract)", command=lambda: self.run_workflow("extract")).pack(pady=5, fill="x")
        ttk.Button(char_step_frame, text="合并角色信息 (merge)", command=lambda: self.run_workflow("merge")).pack(pady=5, fill="x")
        ttk.Button(char_step_frame, text="生成角色卡 (create)", command=lambda: self.run_workflow("create")).pack(pady=5, fill="x")

        # Step-by-step Commands (Worldbook)
        wb_step_frame = ttk.LabelFrame(parent_frame, text="世界书分步流程")
        wb_step_frame.pack(padx=10, pady=5, fill="x")

        ttk.Button(wb_step_frame, text="提取世界观条目 (wb-extract)", command=lambda: self.run_workflow("wb-extract")).pack(pady=5, fill="x")
        ttk.Button(wb_step_frame, text="生成世界书 (wb-generate)", command=lambda: self.run_workflow("wb-generate")).pack(pady=5, fill="x")

        # Other Commands
        other_frame = ttk.LabelFrame(parent_frame, text="其他命令")
        other_frame.pack(padx=10, pady=5, fill="x")

        ttk.Button(other_frame, text="查看状态 (status)", command=lambda: self.run_workflow("status")).pack(pady=5, fill="x")
        ttk.Button(other_frame, text="清理文件 (clean)", command=lambda: self.run_workflow("clean")).pack(pady=5, fill="x")
        ttk.Button(other_frame, text="显示帮助 (help)", command=lambda: self.run_workflow("help")).pack(pady=5, fill="x")

    def load_config(self, config_file_path):
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            self.populate_config_fields()
            self.log_message(f"配置加载成功: {config_file_path}")
        except FileNotFoundError:
            messagebox.showerror("错误", f"配置文件未找到: {config_file_path}")
            self.log_message(f"错误: 配置文件未找到: {config_file_path}")
        except yaml.YAMLError as e:
            messagebox.showerror("错误", f"解析配置文件时出错: {e}")
            self.log_message(f"错误: 解析配置文件时出错: {e}")

    def populate_config_fields(self):
        # API
        for field, entry in self.api_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, self.config_data.get(field, ""))

        # Input/Output
        for field, entry in self.io_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, self.config_data.get(field, ""))

        # Text Splitting
        if "max_chunk_chars" in self.config_data:
            self.text_split_entries["max_chunk_chars"].delete(0, tk.END)
            self.text_split_entries["max_chunk_chars"].insert(0, self.config_data["max_chunk_chars"])
        if "buffer_chars" in self.config_data:
            self.text_split_entries["buffer_chars"].delete(0, tk.END)
            self.text_split_entries["buffer_chars"].insert(0, self.config_data["buffer_chars"])
        if "chapter_patterns" in self.config_data and self.config_data["chapter_patterns"] is not None:
            self.chapter_patterns_text.delete(1.0, tk.END)
            self.chapter_patterns_text.insert(tk.END, "\n".join(self.config_data["chapter_patterns"]))
        else:
            self.chapter_patterns_text.delete(1.0, tk.END) # Clear if no patterns

        # Performance Optimization
        if "max_concurrent" in self.config_data:
            self.perf_opt_entries["max_concurrent"].delete(0, tk.END)
            self.perf_opt_entries["max_concurrent"].insert(0, self.config_data["max_concurrent"])
        if "retry_limit" in self.config_data:
            self.perf_opt_entries["retry_limit"].delete(0, tk.END)
            self.perf_opt_entries["retry_limit"].insert(0, self.config_data["retry_limit"])
        if "retry_delay" in self.config_data:
            self.perf_opt_entries["retry_delay"].delete(0, tk.END)
            self.perf_opt_entries["retry_delay"].insert(0, self.config_data["retry_delay"])
        if "max_test_chunks" in self.config_data:
            self.perf_opt_entries["max_test_chunks"].delete(0, tk.END)
            self.perf_opt_entries["max_test_chunks"].insert(0, self.config_data["max_test_chunks"])
        if "rate_limit_delay" in self.config_data:
            self.perf_opt_entries["rate_limit_delay"].delete(0, tk.END)
            self.perf_opt_entries["rate_limit_delay"].insert(0, self.config_data["rate_limit_delay"])
        if "batch_size" in self.config_data:
            self.perf_opt_entries["batch_size"].delete(0, tk.END)
            self.perf_opt_entries["batch_size"].insert(0, self.config_data["batch_size"])

        self.test_mode_var.set(self.config_data.get("test_mode", False))
        self.enable_cache_var.set(self.config_data.get("enable_cache", False))
        self.cache_dir_entry.delete(0, tk.END)
        self.cache_dir_entry.insert(0, self.config_data.get("cache_dir", ""))
        self.cache_expiry_days_entry.delete(0, tk.END)
        self.cache_expiry_days_entry.insert(0, self.config_data.get("cache_expiry_days", ""))

        # Character Analysis
        if "character_extraction_prompt" in self.config_data:
            self.char_extraction_prompt_text.delete(1.0, tk.END)
            self.char_extraction_prompt_text.insert(tk.END, self.config_data["character_extraction_prompt"])
        else:
            self.char_extraction_prompt_text.delete(1.0, tk.END)

        # Name Normalization
        name_norm = self.config_data.get("name_normalization", {})
        self.name_norm_enable_var.set(name_norm.get("enable", False))
        self.similarity_threshold_entry.delete(0, tk.END)
        self.similarity_threshold_entry.insert(0, name_norm.get("similarity_threshold", ""))
        self.merge_similar_names_var.set(name_norm.get("merge_similar_names", False))

        # Worldbook
        if "worldbook_extraction_prompt" in self.config_data:
            self.wb_extraction_prompt_text.delete(1.0, tk.END)
            self.wb_extraction_prompt_text.insert(tk.END, self.config_data["worldbook_extraction_prompt"])
        else:
            self.wb_extraction_prompt_text.delete(1.0, tk.END)

        # SillyTavern Worldbook
        st_wb = self.config_data.get("sillytavern_worldbook", {})
        for field, entry in self.st_wb_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, st_wb.get(field, ""))
        self.recursive_scanning_var.set(st_wb.get("recursive_scanning", False))
        self.case_sensitive_var.set(st_wb.get("case_sensitive", False))
        self.match_whole_words_var.set(st_wb.get("match_whole_words", False))

        # Default Entry Settings
        default_entry = st_wb.get("default_entry", {})
        for field, entry in self.default_entry_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, default_entry.get(field, ""))
        self.default_entry_enabled_var.set(default_entry.get("enabled", False))

        # Character Card Enhancement
        char_card = self.config_data.get("character_card", {})
        for field, var in self.char_card_vars.items():
            var.set(char_card.get(field, False))
        self.alternate_greetings_count_entry.delete(0, tk.END)
        self.alternate_greetings_count_entry.insert(0, char_card.get("alternate_greetings_count", ""))
        self.max_tags_entry.delete(0, tk.END)
        self.max_tags_entry.insert(0, char_card.get("max_tags", ""))
        self.creator_entry.delete(0, tk.END)
        self.creator_entry.insert(0, char_card.get("creator", ""))
        self.character_version_entry.delete(0, tk.END)
        self.character_version_entry.insert(0, char_card.get("character_version", ""))

        # Log Configuration
        for field, entry in self.log_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, self.config_data.get(field, ""))
        self.verbose_logging_var.set(self.config_data.get("verbose_logging", False))

        # Advanced Configuration
        model_params = self.config_data.get("model_parameters", {})
        for field, entry in self.model_params_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, model_params.get(field, ""))

        error_handling = self.config_data.get("error_handling", {})
        self.continue_on_error_var.set(error_handling.get("continue_on_error", False))
        self.save_error_details_var.set(error_handling.get("save_error_details", False))
        self.max_consecutive_errors_entry.delete(0, tk.END)
        self.max_consecutive_errors_entry.insert(0, error_handling.get("max_consecutive_errors", ""))

        output_format = self.config_data.get("output_format", {})
        self.ensure_ascii_var.set(output_format.get("ensure_ascii", False))
        self.indent_entry.delete(0, tk.END)
        self.indent_entry.insert(0, output_format.get("indent", ""))
        self.sort_keys_var.set(output_format.get("sort_keys", False))

        # Experimental Features
        experimental = self.config_data.get("experimental", {})
        for field, var in self.exp_vars.items():
            var.set(experimental.get(field, False))


    def save_config(self):
        try:
            # Update config_data from UI fields
            for field, entry in self.api_entries.items():
                self.config_data[field] = entry.get()

            for field, entry in self.io_entries.items():
                self.config_data[field] = entry.get()

            # Text Splitting
            self.config_data["max_chunk_chars"] = int(self.text_split_entries["max_chunk_chars"].get())
            self.config_data["buffer_chars"] = int(self.text_split_entries["buffer_chars"].get())
            self.config_data["chapter_patterns"] = [line.strip() for line in self.chapter_patterns_text.get(1.0, tk.END).split('\n') if line.strip()]

            # Performance Optimization
            self.config_data["max_concurrent"] = int(self.perf_opt_entries["max_concurrent"].get())
            self.config_data["retry_limit"] = int(self.perf_opt_entries["retry_limit"].get())
            self.config_data["retry_delay"] = int(self.perf_opt_entries["retry_delay"].get())
            self.config_data["test_mode"] = self.test_mode_var.get()
            self.config_data["max_test_chunks"] = int(self.perf_opt_entries["max_test_chunks"].get())
            self.config_data["rate_limit_delay"] = int(self.perf_opt_entries["rate_limit_delay"].get())
            self.config_data["batch_size"] = int(self.perf_opt_entries["batch_size"].get())
            self.config_data["enable_cache"] = self.enable_cache_var.get()
            self.config_data["cache_dir"] = self.cache_dir_entry.get()
            self.config_data["cache_expiry_days"] = int(self.cache_expiry_days_entry.get())

            # Character Analysis
            self.config_data["character_extraction_prompt"] = self.char_extraction_prompt_text.get(1.0, tk.END).strip()

            # Name Normalization
            self.config_data["name_normalization"]["enable"] = self.name_norm_enable_var.get()
            self.config_data["name_normalization"]["similarity_threshold"] = float(self.similarity_threshold_entry.get())
            self.config_data["name_normalization"]["merge_similar_names"] = self.merge_similar_names_var.get()

            # Worldbook
            self.config_data["worldbook_extraction_prompt"] = self.wb_extraction_prompt_text.get(1.0, tk.END).strip()

            # SillyTavern Worldbook
            st_wb = self.config_data.get("sillytavern_worldbook", {})
            for field, entry in self.st_wb_entries.items():
                st_wb[field] = entry.get()
            st_wb["scan_depth"] = int(st_wb["scan_depth"])
            st_wb["token_budget"] = int(st_wb["token_budget"])
            st_wb["recursive_scanning"] = self.recursive_scanning_var.get()
            st_wb["case_sensitive"] = self.case_sensitive_var.get()
            st_wb["match_whole_words"] = self.match_whole_words_var.get()
            self.config_data["sillytavern_worldbook"] = st_wb

            # Default Entry Settings
            default_entry = st_wb.get("default_entry", {})
            for field, entry in self.default_entry_entries.items():
                default_entry[field] = int(entry.get())
            default_entry["enabled"] = self.default_entry_enabled_var.get()
            st_wb["default_entry"] = default_entry

            # Character Card Enhancement
            char_card = self.config_data.get("character_card", {})
            for field, var in self.char_card_vars.items():
                char_card[field] = var.get()
            char_card["alternate_greetings_count"] = int(self.alternate_greetings_count_entry.get())
            char_card["max_tags"] = int(self.max_tags_entry.get())
            char_card["creator"] = self.creator_entry.get()
            char_card["character_version"] = self.character_version_entry.get()
            self.config_data["character_card"] = char_card

            # Log Configuration
            for field, entry in self.log_entries.items():
                self.config_data[field] = entry.get()
            self.config_data["verbose_logging"] = self.verbose_logging_var.get()

            # Advanced Configuration
            model_params = self.config_data.get("model_parameters", {})
            for field, entry in self.model_params_entries.items():
                model_params[field] = float(entry.get()) if field == "temperature" else int(entry.get())
            self.config_data["model_parameters"] = model_params

            error_handling = self.config_data.get("error_handling", {})
            error_handling["continue_on_error"] = self.continue_on_error_var.get()
            error_handling["save_error_details"] = self.save_error_details_var.get()
            error_handling["max_consecutive_errors"] = int(self.max_consecutive_errors_entry.get())
            self.config_data["error_handling"] = error_handling

            output_format = self.config_data.get("output_format", {})
            output_format["ensure_ascii"] = self.ensure_ascii_var.get()
            output_format["indent"] = int(self.indent_entry.get())
            output_format["sort_keys"] = self.sort_keys_var.get()
            self.config_data["output_format"] = output_format

            # Experimental Features
            experimental = self.config_data.get("experimental", {})
            for field, var in self.exp_vars.items():
                experimental[field] = var.get()
            self.config_data["experimental"] = experimental


            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, allow_unicode=True, sort_keys=False)
            messagebox.showinfo("成功", "配置已保存。")
            self.log_message("配置已成功保存。")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时出错: {e}")
            self.log_message(f"错误: 保存配置时出错: {e}")

    def run_workflow(self, command):
        self.log_message(f"正在执行命令: python {WORKFLOW_SCRIPT} {command}")
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"\n--- 正在执行: python {WORKFLOW_SCRIPT} {command} ---\n")
        self.log_text.config(state='disabled')
        try:
            # Ensure the script is run from its directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            process = subprocess.Popen(
                ["python", WORKFLOW_SCRIPT, command],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            for line in iter(process.stdout.readline, ''):
                self.log_message(line.strip())
            for line in iter(process.stderr.readline, ''):
                self.log_message(f"错误: {line.strip()}")

            process.wait()
            if process.returncode == 0:
                self.log_message(f"命令 '{command}' 执行成功。")
            else:
                self.log_message(f"命令 '{command}' 执行失败，退出码: {process.returncode}")

        except FileNotFoundError:
            messagebox.showerror("错误", f"Python 或 {WORKFLOW_SCRIPT} 未找到。请确保它们在系统PATH中或路径正确。")
            self.log_message(f"错误: Python 或 {WORKFLOW_SCRIPT} 未找到。")
        except Exception as e:
            messagebox.showerror("错误", f"执行命令时出错: {e}")
            self.log_message(f"错误: 执行命令时出错: {e}")
        finally:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"\n--- 命令 '{command}' 执行完成 ---\n")
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END) # Scroll to the end

    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END) # Scroll to the end

    def browse_config_file(self):
        file_path = filedialog.askopenfilename(
            title="选择 config.yaml 文件",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")])
        if file_path:
            self.load_config(file_path)

    def browse_input_file(self):
        file_path = filedialog.askopenfilename(
            title="选择小说文本文件 (mrly.txt)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            self.io_entries["input_file"].delete(0, tk.END)
            self.io_entries["input_file"].insert(0, os.path.basename(file_path)) # Only save filename, not full path
            self.log_message(f"已选择输入文件: {file_path}。请确保此文件位于项目根目录或手动复制。")

if __name__ == "__main__":
    root = tk.Tk()
    app = STBookApp(root)
    root.mainloop()
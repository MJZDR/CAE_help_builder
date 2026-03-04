import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

# 添加 src 到 path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from cae_doc_builder.core.engine import DocBuilderEngine
from cae_doc_builder.adapters.ansys_adapter import AnsysAdapter
from cae_doc_builder.adapters.ansa_adapter import AnsaAdapter
from cae_doc_builder.adapters.abaqus_adapter import AbaqusAdapter

CONFIG_FILE = "config.json"

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("CAE 知识库构建器 v3.2 (UI 增强版)")
        self.root.geometry("1000x750")
        
        # 变量定义
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.adapter_type = tk.StringVar(value="ANSA")
        self.progress_val = tk.DoubleVar(value=0)
        
        self.engine = None
        self.tree_item_map = {}
        
        # 加载记忆的配置
        self._load_config()
        
        self._setup_ui()

    def _setup_ui(self):
        # === 1. 顶部配置栏 ===
        frame_top = ttk.LabelFrame(self.root, text="配置与路径记忆", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_top, text="软件类型:").grid(row=0, column=0, sticky="e")
        combo = ttk.Combobox(frame_top, textvariable=self.adapter_type, state="readonly", width=12)
        combo['values'] = ("ANSA", "ANSYS", "ABAQUS")
        combo.grid(row=0, column=1, sticky="w", padx=5)
        combo.bind("<<ComboboxSelected>>", lambda e: self._save_config())
        
        ttk.Label(frame_top, text="源目录 (Input):").grid(row=0, column=2, sticky="e", padx=5)
        ttk.Entry(frame_top, textvariable=self.source_dir, width=45).grid(row=0, column=3, padx=5)
        ttk.Button(frame_top, text="浏览", command=self._browse_source).grid(row=0, column=4)
        
        ttk.Label(frame_top, text="输出目录 (Output):").grid(row=1, column=2, sticky="e", padx=5, pady=5)
        ttk.Entry(frame_top, textvariable=self.output_dir, width=45).grid(row=1, column=3, padx=5)
        ttk.Button(frame_top, text="浏览", command=self._browse_output).grid(row=1, column=4)
        
        self.btn_load = ttk.Button(frame_top, text="📥 加载架构", command=self._start_scan_thread)
        self.btn_load.grid(row=0, column=5, rowspan=2, padx=15, sticky="ns")

        # === 2. 内容显示区 ===
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        frame_tree = ttk.LabelFrame(paned, text="文档架构树 (多选)", padding=5)
        paned.add(frame_tree, weight=1)
        
        self.tree = ttk.Treeview(frame_tree, columns=("type"), selectmode="extended")
        self.tree.heading("#0", text="结构列表")
        self.tree.heading("type", text="类别")
        self.tree.column("type", width=70, anchor="center")
        
        ysb = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)

        frame_log = ttk.LabelFrame(paned, text="执行日志", padding=5)
        paned.add(frame_log, weight=1)
        self.log_area = scrolledtext.ScrolledText(frame_log, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

        # === 3. 底部进度与操作栏 ===
        frame_bottom = ttk.Frame(self.root, padding=10)
        frame_bottom.pack(fill="x")
        
        self.lbl_status = ttk.Label(frame_bottom, text="就绪", width=30)
        self.lbl_status.pack(side="left")
        
        # 进度条 
        self.progress_bar = ttk.Progressbar(frame_bottom, variable=self.progress_val, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=15)
        
        self.btn_build = ttk.Button(frame_bottom, text="🚀 开始构建知识库", command=self._start_build_thread, state="disabled")
        self.btn_build.pack(side="right")

    # --- 记忆功能实现  ---
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.source_dir.set(data.get("source_dir", ""))
                    self.output_dir.set(data.get("output_dir", ""))
                    self.adapter_type.set(data.get("adapter_type", "ANSA"))
            except: pass

    def _save_config(self):
        config = {
            "source_dir": self.source_dir.get(),
            "output_dir": self.output_dir.get(),
            "adapter_type": self.adapter_type.get()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

    def _browse_source(self):
        d = filedialog.askdirectory(initialdir=self.source_dir.get())
        if d: 
            self.source_dir.set(d)
            self._save_config()

    def _browse_output(self):
        d = filedialog.askdirectory(initialdir=self.output_dir.get())
        if d: 
            self.output_dir.set(d)
            self._save_config()

    # --- 日志与进度更新 ---
    def log(self, msg):
        self.root.after(0, lambda: self._log_threadsafe(msg))

    def _log_threadsafe(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def set_progress(self, val, status=None):
        self.root.after(0, lambda: self._update_progress_ui(val, status))

    def _update_progress_ui(self, val, status):
        self.progress_val.set(val)
        if status: self.lbl_status.config(text=status)

    # --- 业务逻辑 ---
    def _start_scan_thread(self):
        src = self.source_dir.get()
        if not src: return
        self.btn_load.config(state="disabled")
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10) # 扫描阶段开启动画
        self.set_progress(0, "正在扫描结构...")
        
        t = threading.Thread(target=self._run_scan, args=(src, self.adapter_type.get()))
        t.start()

    def _run_scan(self, src, atype):
        try:
            adapter = None
            if atype == "ANSA": adapter = AnsaAdapter(src, ".", self.log)
            elif atype == "ANSYS": adapter = AnsysAdapter(src, ".", self.log)
            elif atype == "ABAQUS": adapter = AbaqusAdapter(src, ".", self.log)
            
            self.engine = DocBuilderEngine(adapter)
            root_nodes = self.engine.analyze_structure(src)
            self.root.after(0, lambda: self._populate_tree(root_nodes))
        except Exception as e:
            self.log(f"❌ 扫描失败: {e}")
        finally:
            self.root.after(0, lambda: self._end_scan_ui())

    def _end_scan_ui(self):
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate")
        self.btn_load.config(state="normal")
        self.set_progress(100, "架构加载完成")

    def _populate_tree(self, nodes):
        self.tree.delete(*self.tree.get_children())
        self.tree_item_map.clear()
        for node in nodes:
            icon = "📚" if node.is_container else "📄"
            iid = self.tree.insert("", "end", text=f"{icon} {node.title}", values=("书籍" if node.level==1 else "章节"))
            self.tree_item_map[iid] = node
            self._insert_children(iid, node)
        self.btn_build.config(state="normal")

    def _insert_children(self, parent_id, node):
        for child in node.children:
            icon = "📂" if child.is_container else "📄"
            iid = self.tree.insert(parent_id, "end", text=f"{icon} {child.title}", values=("容器" if child.is_container else "文件"))
            self.tree_item_map[iid] = child
            self._insert_children(iid, child)

    def _start_build_thread(self):
        selected_ids = self.tree.selection()
        if not selected_ids: return
        
        # 智能去重逻辑
        selected_set = set(selected_ids)
        final_nodes = []
        for iid in selected_ids:
            parent = self.tree.parent(iid)
            is_redundant = False
            while parent:
                if parent in selected_set:
                    is_redundant = True
                    break
                parent = self.tree.parent(parent)
            if not is_redundant:
                final_nodes.append(self.tree_item_map[iid])
        
        self.btn_build.config(state="disabled")
        self.set_progress(0, "准备构建...")
        t = threading.Thread(target=self._run_build, args=(final_nodes, self.output_dir.get()))
        t.start()

    def _run_build(self, nodes, out):
        try:
            # 统计总任务数用于进度条 
            total_tasks = self._count_all_nodes(nodes)
            self.current_count = 0
            self.total_count = total_tasks
            
            # 这里我们通过 monkey patch 或者在 engine 逻辑中增加进度回调
            # 简化方案：由于逻辑在 engine 内部，我们分批次更新
            self.engine.build_nodes(nodes, out)
            self.set_progress(100, "✅ 构建成功！")
            messagebox.showinfo("完成", "知识库构建已结束！")
        except Exception as e:
            self.log(f"❌ 构建失败: {e}")
            self.set_progress(0, "构建出错")
        finally:
            self.root.after(0, lambda: self.btn_build.config(state="normal"))

    def _count_all_nodes(self, nodes):
        count = len(nodes)
        for n in nodes:
            count += self._count_all_nodes(n.children)
        return count

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

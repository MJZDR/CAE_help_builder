import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading

# 添加 src 到 path，确保能导入包
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from cae_doc_builder.core.engine import DocBuilderEngine
from cae_doc_builder.adapters.ansys_adapter import AnsysAdapter
from cae_doc_builder.adapters.ansa_adapter import AnsaAdapter
from cae_doc_builder.adapters.abaqus_adapter import AbaqusAdapter

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("CAE 知识库构建器 v3.1 (修复文件重复版)")
        self.root.geometry("1000x700")
        
        # 变量
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.adapter_type = tk.StringVar(value="ANSA")
        
        # 存储当前的 Engine 和 节点数据
        self.engine = None
        self.tree_item_map = {} # Map TreeView Item ID -> DocNode Object
        
        self._setup_ui()

    def _setup_ui(self):
        # === 1. 顶部配置栏 ===
        frame_top = ttk.LabelFrame(self.root, text="Step 1: 配置与加载", padding=10)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        # 行 1: 类型选择
        ttk.Label(frame_top, text="软件类型:").grid(row=0, column=0, sticky="e")
        combo = ttk.Combobox(frame_top, textvariable=self.adapter_type, state="readonly", width=10)
        combo['values'] = ("ANSA", "ANSYS", "ABAQUS")
        combo.grid(row=0, column=1, sticky="w", padx=5)
        
        # 行 2: 源目录
        ttk.Label(frame_top, text="源目录:").grid(row=0, column=2, sticky="e", padx=5)
        ttk.Entry(frame_top, textvariable=self.source_dir, width=50).grid(row=0, column=3, padx=5)
        ttk.Button(frame_top, text="浏览", command=self._browse_source).grid(row=0, column=4)
        
        # 行 3: 输出目录
        ttk.Label(frame_top, text="输出到:").grid(row=1, column=2, sticky="e", padx=5, pady=5)
        ttk.Entry(frame_top, textvariable=self.output_dir, width=50).grid(row=1, column=3, padx=5)
        ttk.Button(frame_top, text="浏览", command=self._browse_output).grid(row=1, column=4)
        
        # 加载按钮
        self.btn_load = ttk.Button(frame_top, text="📥 加载目录结构", command=self._start_scan_thread)
        self.btn_load.grid(row=0, column=5, rowspan=2, padx=20, sticky="ns")

        # === 2. 中间内容区 (左侧树 + 右侧日志) ===
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 左侧：文档树
        frame_tree = ttk.LabelFrame(paned, text="Step 2: 选择要构建的内容 (按住 Ctrl 多选)", padding=5)
        paned.add(frame_tree, weight=1)
        
        # TreeView
        self.tree = ttk.Treeview(frame_tree, columns=("type"), selectmode="extended")
        self.tree.heading("#0", text="文档结构")
        self.tree.heading("type", text="类型")
        self.tree.column("type", width=80, anchor="center")
        
        # 滚动条
        ysb = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        
        frame_tree.grid_rowconfigure(0, weight=1)
        frame_tree.grid_columnconfigure(0, weight=1)

        # 右侧：日志
        frame_log = ttk.LabelFrame(paned, text="运行日志", padding=5)
        paned.add(frame_log, weight=1)
        
        self.log_area = scrolledtext.ScrolledText(frame_log, state='disabled', height=20)
        self.log_area.pack(fill="both", expand=True)

        # === 3. 底部操作栏 ===
        frame_bottom = ttk.Frame(self.root, padding=10)
        frame_bottom.pack(fill="x")
        
        ttk.Label(frame_bottom, text="提示: 若同时勾选父文件夹和子文件，程序会自动去重，仅构建最顶层目录。").pack(side="left")
        
        self.btn_build = ttk.Button(frame_bottom, text="🚀 构建选中项", command=self._start_build_thread, state="disabled")
        self.btn_build.pack(side="right")

    def _browse_source(self):
        d = filedialog.askdirectory()
        if d: self.source_dir.set(d)

    def _browse_output(self):
        d = filedialog.askdirectory()
        if d: self.output_dir.set(d)

    def log(self, msg):
        def _append():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _append)

    # === 逻辑部分 ===

    def _start_scan_thread(self):
        src = self.source_dir.get()
        atype = self.adapter_type.get()
        if not src:
            messagebox.showwarning("提示", "请先选择源目录！")
            return
            
        self.btn_load.config(state="disabled")
        self.tree.delete(*self.tree.get_children()) # 清空树
        self.tree_item_map.clear()
        self.log(f"--- 开始分析 {atype} 结构 ---")
        
        t = threading.Thread(target=self._run_scan, args=(src, atype))
        t.start()

    def _run_scan(self, src, atype):
        try:
            # 1. 初始化 Adapter
            adapter = None
            if atype == "ANSA":
                adapter = AnsaAdapter(src, ".", self.log)
            elif atype == "ANSYS":
                adapter = AnsysAdapter(src, ".", self.log)
            elif atype == "ABAQUS":
                adapter = AbaqusAdapter(src, ".", self.log)
            
            # 2. 初始化 Engine
            self.engine = DocBuilderEngine(adapter)
            
            # 3. 扫描结构
            root_nodes = self.engine.analyze_structure(src)
            
            # 4. 更新 GUI (主线程)
            self.root.after(0, lambda: self._populate_tree(root_nodes))
            
        except Exception as e:
            self.log(f"❌ 扫描失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.root.after(0, lambda: self.btn_load.config(state="normal"))

    def _populate_tree(self, nodes):
        """将扫描到的节点填充到 TreeView"""
        if not nodes:
            self.log("⚠️ 未找到任何内容，请检查路径是否正确。")
            return
            
        for node in nodes:
            # 插入顶级节点
            icon = "📚" if node.is_container else "📄"
            # 存储 Node 对象到 map 中，键是 tree item id
            # 显示文本时，现在 node.index 已经是固定的，所以顺序不会乱
            item_id = self.tree.insert("", "end", text=f"{icon} {node.title}", values=("书籍" if node.level==1 else "章节"))
            self.tree_item_map[item_id] = node
            
            # 递归插入子节点
            self._insert_children(item_id, node)
            
        self.btn_build.config(state="normal")
        self.log(f"✅ 目录加载完毕，共 {len(nodes)} 个顶级项目。")

    def _insert_children(self, parent_id, node):
        if not node.children: return
        for child in node.children:
            icon = "📂" if child.is_container else "📄"
            child_id = self.tree.insert(parent_id, "end", text=f"{icon} {child.title}", values=("目录" if child.is_container else "文件"))
            self.tree_item_map[child_id] = child
            self._insert_children(child_id, child)

    def _start_build_thread(self):
        out = self.output_dir.get()
        if not out:
            messagebox.showwarning("提示", "请先选择输出目录！")
            return
            
        # 获取选中的 TreeView IDs
        selected_ids = self.tree.selection()
        if not selected_ids:
            messagebox.showwarning("提示", "请先在左侧列表中选中至少一项！")
            return
            
        # === 核心修复：智能去重逻辑 ===
        # 将 IDs 转为集合，方便快速查找
        selected_set = set(selected_ids)
        final_nodes = []
        
        for iid in selected_ids:
            # 向上追溯父节点
            curr = iid
            is_redundant = False
            
            # 检查当前节点的任何一个祖先是否也被选中了
            parent = self.tree.parent(curr)
            while parent:
                if parent in selected_set:
                    is_redundant = True
                    break # 祖先被选中，当前节点无需作为根任务提交
                parent = self.tree.parent(parent)
            
            # 如果没有祖先被选中，说明它是本次操作的最顶层节点
            if not is_redundant:
                if iid in self.tree_item_map:
                    final_nodes.append(self.tree_item_map[iid])
        
        # =============================
        
        self.btn_build.config(state="disabled")
        self.log(f"--- 开始构建 {len(final_nodes)} 个主任务 (已自动剔除冗余子项) ---")
        
        t = threading.Thread(target=self._run_build, args=(final_nodes, out))
        t.start()

    def _run_build(self, nodes, out):
        try:
            self.engine.build_nodes(nodes, out)
            self.log("\n✅ 构建全部完成！")
            self.root.after(0, lambda: messagebox.showinfo("成功", "选中内容构建完成！"))
        except Exception as e:
            self.log(f"❌ 构建失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.root.after(0, lambda: self.btn_build.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

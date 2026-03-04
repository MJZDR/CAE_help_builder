import os
import re
from ..utils.path_utils import PathUtils

class DocBuilderEngine:
    def __init__(self, adapter, converter=None):
        self.adapter = adapter
        self.total_nodes = 0
        self.processed_nodes = 0
        self.progress_callback = None

    def analyze_structure(self, source_path):
        """扫描结构入口"""
        if hasattr(self.adapter, 'src_root'):
            self.adapter.src_root = source_path
        return self.adapter.parse_structure()

    def build_nodes(self, nodes_to_build, output_root, progress_callback=None):
        """构建入口，支持进度回调"""
        self.total_nodes = self._count_nodes(nodes_to_build)
        self.processed_nodes = 0
        self.progress_callback = progress_callback
        self._process_nodes_recursive(nodes_to_build, output_root)

    def _process_nodes_recursive(self, nodes, current_out_dir):
        if not os.path.exists(current_out_dir):
            os.makedirs(current_out_dir)

        for node in nodes:
            # 命名规则：如果标题自带编号则不重复加，否则加 Index 前缀
            title_clean = PathUtils.sanitize_filename(node.title)
            if re.match(r'^\d+[.\-]\s*', title_clean):
                safe_name = title_clean
            elif node.index > 0:
                safe_name = f"{node.index}-{title_clean}"
            else:
                safe_name = title_clean
            
            assets_dir = os.path.join(current_out_dir, "assets")

            if node.is_container:
                new_dir = os.path.join(current_out_dir, safe_name)
                os.makedirs(new_dir, exist_ok=True)
                
                # 介绍页：标题.md
                if node.source_path:
                    content = self.adapter.read_file_content(node, image_out_dir=assets_dir)
                    if content:
                        intro_name = PathUtils.sanitize_filename(node.title) + ".md"
                        self._save_file(os.path.join(new_dir, intro_name), content)
                
                if node.children:
                    self._process_nodes_recursive(node.children, new_dir)
            else:
                # 叶子节点直接生成文件
                md_path = os.path.join(current_out_dir, f"{safe_name}.md")
                content = self.adapter.read_file_content(node, image_out_dir=assets_dir)
                self._save_file(md_path, content)
            
            # 更新进度
            self.processed_nodes += 1
            if self.progress_callback:
                self.progress_callback(self.processed_nodes, self.total_nodes)

    def _count_nodes(self, nodes):
        count = len(nodes)
        for n in nodes:
            count += self._count_nodes(n.children)
        return count

    def _save_file(self, path, content):
        if not content: return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Write Error: {e}")

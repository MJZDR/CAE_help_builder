import os
from ..utils.path_utils import PathUtils

class DocBuilderEngine:
    def __init__(self, adapter, converter=None):
        self.adapter = adapter

    def analyze_structure(self, source_path):
        if hasattr(self.adapter, 'src_root'):
            self.adapter.src_root = source_path
        return self.adapter.parse_structure()

    def build_nodes(self, nodes_to_build, output_root):
        self._process_nodes_recursive(nodes_to_build, output_root)

    def _process_nodes_recursive(self, nodes, current_out_dir):
        if not os.path.exists(current_out_dir):
            os.makedirs(current_out_dir)

        for node in nodes:
            # 核心修改：使用节点扫描时预存的固定编号 node.index
            safe_name = PathUtils.generate_name(node.title, node.index)
            assets_dir = os.path.join(current_out_dir, "assets")

            if node.is_container:
                new_dir = os.path.join(current_out_dir, safe_name)
                if node.source_path:
                    content = self.adapter.read_file_content(node, image_out_dir=assets_dir)
                    if content:
                        self._save_file(os.path.join(new_dir, "00_Introduction.md"), content)
                
                if node.children:
                    self._process_nodes_recursive(node.children, new_dir)
            else:
                md_path = os.path.join(current_out_dir, f"{safe_name}.md")
                content = self.adapter.read_file_content(node, image_out_dir=assets_dir)
                self._save_file(md_path, content)

    def _save_file(self, path, content):
        if content is None: return # 支持 PDF 复制等直接处理任务
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Write Error: {e}")

import os
from bs4 import BeautifulSoup
from .base import BaseAdapter
from ..core.structures import DocNode

class AnsaAdapter(BaseAdapter):
    def __init__(self, source_root, out_root, logger_func):
        super().__init__(source_root, out_root, logger_func)
        self.IGNORE_DIRS = {'_static', '_images', '_sources', '__pycache__'}

    def parse_structure(self) -> list[DocNode]:
        self.log(f"🚀 [ANSA] 扫描物理目录并锁定编号: {self.src_root}")
        root_nodes = []
        try:
            items = sorted([d for d in os.listdir(self.src_root) if d not in self.IGNORE_DIRS])
            for i, item_name in enumerate(items, start=1):
                full_path = os.path.join(self.src_root, item_name)
                node = self._build_node_recursive(full_path, level=1, index=i)
                if node: root_nodes.append(node)
        except Exception as e:
            self.log(f"❌ ANSA 扫描异常: {e}")
        return root_nodes

    def _build_node_recursive(self, current_path, level, index):
        if os.path.isdir(current_path):
            folder_name = os.path.basename(current_path)
            index_path = os.path.join(current_path, 'index.html')
            node = DocNode(title=folder_name, level=level, index=index, is_container=True)
            if os.path.exists(index_path): node.source_path = index_path

            sub_items = sorted([d for d in os.listdir(current_path) if d not in self.IGNORE_DIRS])
            for k, sub_name in enumerate(sub_items, start=1):
                child = self._build_node_recursive(os.path.join(current_path, sub_name), level + 1, k)
                if child: node.add_child(child)
            return node
        elif current_path.endswith('.html') and 'index.html' not in current_path:
            return DocNode(title=os.path.basename(current_path), level=level, index=index, source_path=current_path)
        return None

    def read_file_content(self, node: DocNode, image_out_dir: str = None) -> str:
        if not node.source_path: return ""
        try:
            with open(node.source_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            for side in soup.select('div.sphinxsidebar, footer'): side.decompose()
            content = soup.find('div', role='main') or soup.body
            return content.get_text() if content else ""
        except: return ""

    def process_task(self, task): pass

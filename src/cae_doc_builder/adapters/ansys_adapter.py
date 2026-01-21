import os
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from .base import BaseAdapter
from ..core.structures import DocNode
from ..converters.html_md import ContentConverter

class AnsysAdapter(BaseAdapter):
    def __init__(self, src_root, out_root, logger_func):
        super().__init__(src_root, out_root, logger_func)
        self.converter = ContentConverter()

    def parse_structure(self) -> list[DocNode]:
        self.log("🔍 [Ansys] 正在解析 toc_config.xml 并锁定编号...")
        nodes = []
        config_path = os.path.join(self.src_root, "toc_config.xml")
        if not os.path.exists(config_path): return []

        try:
            tree = ET.parse(config_path)
            for i, child in enumerate(tree.getroot(), start=1):
                if child.tag == 'set':
                    set_node = DocNode(title=child.get('title'), level=1, index=i, is_container=True)
                    for j, b in enumerate(child.findall("book"), start=1):
                        book_node = self._create_book_node(b, j)
                        if book_node: set_node.add_child(book_node)
                    nodes.append(set_node)
                elif child.tag == 'book':
                    book_node = self._create_book_node(child, i)
                    if book_node: nodes.append(book_node)
            return nodes
        except Exception as e:
            self.log(f"❌ Ansys 扫描失败: {e}")
            return []

    def _create_book_node(self, xml_node, idx) -> DocNode:
        path = xml_node.get("path")
        label = xml_node.get("label") or xml_node.get("title") or path
        node = DocNode(title=label, level=2, index=idx, is_container=True)
        node.source_path = os.path.join(self.src_root, "help", path, "index.html")
        
        toc_file = os.path.join(self.src_root, "help", path, "toc.toc")
        if os.path.exists(toc_file):
            self._parse_ansys_toc_recursive(toc_file, node)
        return node

    def _parse_ansys_toc_recursive(self, toc_file, parent_node):
        try:
            with open(toc_file, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            root_dl = soup.find('dl')
            if root_dl: self._build_ansys_tree(root_dl, parent_node, os.path.dirname(toc_file), 3)
        except: pass

    def _build_ansys_tree(self, dl, parent_node, base_dir, level):
        for i, dt in enumerate(dl.find_all('dt', recursive=False), start=1):
            a = dt.find('a')
            if not a: continue
            href = a.get('href', '').split('#')[0]
            node = DocNode(title=a.get_text().strip(), level=level, index=i)
            node.source_path = os.path.normpath(os.path.join(base_dir, href))
            
            dd = dt.find_next_sibling('dd')
            if dd and dd.find('dl'):
                node.is_container = True
                self._build_ansys_tree(dd.find('dl'), node, base_dir, level + 1)
            parent_node.add_child(node)

    def read_file_content(self, node: DocNode, image_out_dir: str = None) -> str:
        if not node.source_path: return ""
        return self.converter.convert_to_string(node.source_path, image_out_dir)

    def process_task(self, task): pass

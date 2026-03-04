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
        self.help_base = os.path.join(self.src_root, "help")

    def parse_structure(self) -> list[DocNode]:
        config_path = os.path.join(self.src_root, "toc_config.xml")
        if not os.path.exists(config_path): return []
        
        nodes = []
        try:
            tree = ET.parse(config_path)
            for i, child in enumerate(tree.getroot(), start=1):
                if child.tag == 'set':
                    node = DocNode(title=child.get('title'), level=1, index=i, is_container=True)
                    if child.get('target'):
                        node.source_path = os.path.normpath(os.path.join(self.help_base, child.get('target')))
                    
                    for j, b in enumerate(child.findall("book"), start=1):
                        book = self._create_book_node(b, 2, j)
                        if book: node.add_child(book)
                    nodes.append(node)
                elif child.tag == 'book':
                    book = self._create_book_node(child, 1, i)
                    if book: nodes.append(book)
            return nodes
        except Exception as e:
            self.log(f"Ansys 扫描失败: {e}")
            return []

    def _create_book_node(self, book_xml, level, index):
        path_attr = book_xml.get('path')
        book_dir = os.path.join(self.help_base, path_attr)
        toc_path = os.path.join(book_dir, "toc.toc")
        if not os.path.exists(toc_path): return None

        with open(toc_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'xml')

        title_tag = soup.find('title')
        title = title_tag.get('title2') or title_tag.get_text().strip()
        
        root_dl = soup.find('dl')
        is_container = root_dl is not None
        
        node = DocNode(title=title, level=level, index=index, is_container=is_container)
        if title_tag.get('href'):
            node.source_path = os.path.normpath(os.path.join(book_dir, title_tag.get('href')))

        if is_container:
            self._recursive_parse_dl(root_dl, node, book_dir, level + 1)
        return node

    def _recursive_parse_dl(self, dl, parent_node, book_dir, level):
        processed_files = set()
        elements = dl.find_all(['dt', 'dd'], recursive=False)
        idx, node_idx = 0, 1
        while idx < len(elements):
            item = elements[idx]
            if item.name == 'dt':
                a = item.find('a')
                if a:
                    title = a.get_text().strip()
                    href = a.get('href', '').split('#')[0]
                    
                    if href and href in processed_files:
                        idx += 1
                        continue
                    if href: processed_files.add(href)
                    
                    # 检查紧随其后的元素是否为 dd 且包含子列表
                    dd = elements[idx+1] if idx+1 < len(elements) and elements[idx+1].name == 'dd' else None
                    child_dl = dd.find('dl') if dd else None
                    has_child = child_dl is not None
                    
                    child_node = DocNode(title=title, level=level, index=node_idx, is_container=has_child)
                    if href:
                        child_node.source_path = os.path.normpath(os.path.join(book_dir, href))
                    
                    parent_node.add_child(child_node)
                    if has_child:
                        self._recursive_parse_dl(child_dl, child_node, book_dir, level + 1)
                    node_idx += 1
            idx += 1

    def read_file_content(self, node: DocNode, image_out_dir: str = None) -> str:
        if not node.source_path: return ""
        return self.converter.convert_to_string(node.source_path, image_out_dir)

    def process_task(self, task): pass

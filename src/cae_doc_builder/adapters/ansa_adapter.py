import os
import shutil
import re
from bs4 import BeautifulSoup
from .base import BaseAdapter
from ..core.structures import DocNode

# 尝试导入 html2text
try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

class AnsaAdapter(BaseAdapter):
    """
    ANSA 适配器 (深度修复版)
    
    修复点：
    1. 增强标题解析逻辑，彻底移除 "- ANSA documentation" 后缀。
    2. 恢复 ver1 中完整的噪音选择器，移除侧边栏、右侧目录、页脚等冗余内容。
    """
    
    def __init__(self, source_root, out_root, logger_func):
        super().__init__(source_root, out_root, logger_func)
        
        # 定义忽略列表 (系统文件、垃圾文件夹)
        self.IGNORE_DIRS = {
            '_static', '_images', '_sources', '_downloads', 
            'search', 'genindex', '.idea', '__pycache__', 'doctrees'
        }
        self.IGNORE_FILES = {'genindex.html', 'search.html', 'licattr.html', '404.html'}
        
        # 初始化转换器
        if HAS_HTML2TEXT:
            self.converter = html2text.HTML2Text()
            self.converter.ignore_links = False
            self.converter.ignore_images = False
            self.converter.body_width = 0
            self.converter.protect_links = True

    def parse_structure(self) -> list[DocNode]:
        """扫描结构并锁定物理编号"""
        self.log(f"🚀 [ANSA] 开始深度扫描结构: {self.src_root}")
        root_nodes = []
        try:
            # 保证扫描顺序
            items = sorted([d for d in os.listdir(self.src_root) if d not in self.IGNORE_DIRS])
            for i, item_name in enumerate(items, start=1):
                full_path = os.path.join(self.src_root, item_name)
                node = self._build_node_recursive(full_path, level=1, index=i)
                if node: root_nodes.append(node)
        except Exception as e:
            self.log(f"❌ ANSA 扫描异常: {e}")
        return root_nodes

    def _build_node_recursive(self, current_path, level, index):
        """递归构建节点树，提取干净标题"""
        if os.path.isdir(current_path):
            folder_name = os.path.basename(current_path)
            index_path = os.path.join(current_path, 'index.html')
            
            node = DocNode(title=folder_name, level=level, index=index, is_container=True)
            
            if os.path.exists(index_path):
                node.source_path = index_path
                # 提取标题并过滤掉后缀
                real_title = self._extract_title_from_html(index_path)
                if real_title: node.title = real_title

            # 递归处理子项
            try:
                sub_items = sorted([d for d in os.listdir(current_path) if d not in self.IGNORE_DIRS])
                child_idx = 1
                for sub_name in sub_items:
                    if sub_name in self.IGNORE_FILES: continue
                    child = self._build_node_recursive(os.path.join(current_path, sub_name), level + 1, child_idx)
                    if child:
                        node.add_child(child)
                        child_idx += 1
            except OSError: pass

            if not node.children and not node.source_path: return None
            return node
        
        elif current_path.endswith('.html'):
            if os.path.basename(current_path).lower() == 'index.html': return None
            title = self._extract_title_from_html(current_path) or os.path.basename(current_path).replace('.html', '')
            return DocNode(title=title, level=level, index=index, source_path=current_path)
        
        return None

    def _extract_title_from_html(self, path):
        """
        [修复点 1] 增强的标题提取与后缀过滤逻辑
        """
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                # 1. 优先从网页 <title> 提取
                if soup.title:
                    raw_title = soup.title.get_text()
                    # 匹配多种分隔符：短横线、长横线、竖线
                    # 过滤掉 "ANSA documentation" 或 "ANSA xxx documentation"
                    clean_title = re.split(r'[-—|]', raw_title)[0].strip()
                    # 针对 ANSA 特有的后缀进行二次清理
                    clean_title = re.sub(r'\s+ANSA\s+documentation$', '', clean_title, flags=re.IGNORECASE)
                    if clean_title: return clean_title

                # 2. 次选 H1
                h1 = soup.find('h1')
                if h1: return h1.get_text().replace('¶', '').strip()
        except: pass
        return None

    def read_file_content(self, node: DocNode, image_out_dir: str = None) -> str:
        """
        [修复点 2] 恢复 ver1 中完整的噪音清洗逻辑
        """
        if not node.source_path or not os.path.exists(node.source_path): return ""

        try:
            with open(node.source_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            # 恢复 ver1 中所有已验证的 ANSA 噪音选择器
            noise_selectors = [
                "div.sphinxsidebar",    # 侧边栏
                "div.related",          # 面包屑导航
                "div.footer", "footer", # 页脚
                "div.related-pages",    # 下一页/上一页按钮
                "a.headerlink",         # 段落符号 ¶
                "script", "style",      # 代码与样式
                "div.toc-drawer",       # 右侧小目录
                "aside",                # 侧边栏辅助容器
                "a.sd-stretched-link"   # 某些卡片主题的覆盖链接
            ]
            for selector in noise_selectors:
                for tag in soup.select(selector):
                    tag.decompose()

            # 定位核心正文 (按照 ANSA 常用主题优先级)
            content = soup.find('div', role='main') or \
                      soup.find('div', itemprop='articleBody') or \
                      soup.find('article') or \
                      soup.body
            
            if not content: content = soup

            # 搬运图片
            if image_out_dir:
                self._handle_images(content, node.source_path, image_out_dir)

            # 转换 Markdown
            if HAS_HTML2TEXT:
                return self.converter.handle(str(content))
            else:
                return content.get_text(separator='\n\n', strip=True)

        except Exception as e:
            self.log(f"⚠️ ANSA 内容提取失败 {node.source_path}: {e}")
            return ""

    def _handle_images(self, soup_element, html_path, out_dir):
        src_dir = os.path.dirname(html_path)
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        for img in soup_element.find_all(['img', 'svg']):
            src = img.get('src')
            if src and not src.startswith(('http', 'data:')):
                abs_src = os.path.normpath(os.path.join(src_dir, src))
                if os.path.exists(abs_src):
                    fname = os.path.basename(abs_src)
                    dst_path = os.path.join(out_dir, fname)
                    if not os.path.exists(dst_path):
                        try: shutil.copy2(abs_src, dst_path)
                        except: pass
                    img['src'] = f"assets/{fname}"

    def process_task(self, task): pass

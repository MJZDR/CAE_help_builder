import os
import shutil
import lxml.etree as ET
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from .base import BaseAdapter
from ..core.structures import DocNode
from ..converters.html_md import ContentConverter
from ..utils.path_utils import PathUtils  # <--- [新增] 导入路径清洗工具

class AbaqusAdapter(BaseAdapter):
    def __init__(self, source_root, out_root, logger_func):
        super().__init__(source_root, out_root, logger_func)
        self.master_toc = "DSSIMULIA_Established_TOC.xml"
        self.converter = ContentConverter()
        self.pdf_items = []

    def parse_structure(self) -> list[DocNode]:
        """解析结构并审计 PDF (保持逻辑不变)"""
        master_path = os.path.join(self.src_root, self.master_toc)
        if not os.path.exists(master_path):
            self.log(f"❌ 找不到 Abaqus 主表文件: {master_path}")
            return []

        root_nodes = []
        self.pdf_items = []
        try:
            parser = ET.XMLParser(recover=True, encoding='utf-8')
            tree = ET.parse(master_path, parser=parser)
            
            # 扫描并锁定顶层编号
            for i, item in enumerate(tree.xpath("/Root/ITEM"), start=1):
                module_name = item.get("name")
                module_node = DocNode(title=module_name, level=1, index=i, 
                                      source_path=self._get_abs_path("", item.get("href")), is_container=True)

                # 扫描并锁定书籍编号 (针对 fe-safe)
                for j, sub_item in enumerate(item.xpath("./DITEM | ./ITEM"), start=1):
                    sub_name = sub_item.get("name")
                    sub_href = sub_item.get("href")
                    child_toc_rel = sub_item.get("childtoc")
                    
                    if sub_href and sub_href.lower().endswith(".pdf"):
                        self.pdf_items.append(sub_name)

                    sub_node = DocNode(title=sub_name, level=2, index=j, 
                                        source_path=self._get_abs_path("", sub_href), 
                                        is_container=True if child_toc_rel or sub_item.xpath("./ITEM") else False)
                    
                    if child_toc_rel:
                        self._parse_child_xml(os.path.join(self.src_root, child_toc_rel), sub_node, os.path.dirname(child_toc_rel), 3)
                    elif sub_item.xpath("./ITEM"):
                        self._walk_internal_items(sub_item, sub_node, 3)
                    module_node.add_child(sub_node)
                root_nodes.append(module_node)

            if self.pdf_items:
                self.log("\n--- 📄 PDF 资源审计报告 ---")
                for pdf_name in self.pdf_items:
                    self.log(f"💡 模块 [{pdf_name}] 指向 PDF，将执行物理复制。")
            self.log("✅ Abaqus 目录架构扫描完成。")
        except Exception as e:
            self.log(f"❌ 解析出错: {str(e)}")
        return root_nodes

    def read_file_content(self, node: DocNode, image_out_dir: str = None) -> str:
        if not node.source_path or not os.path.exists(node.source_path): return ""
        
        # === PDF 复制逻辑 (已修复特殊字符报错) ===
        if node.source_path.lower().endswith(".pdf"):
            try:
                # 确定目标文件夹 (output/Set/assets/..) 的上一级
                dest_dir = os.path.dirname(image_out_dir)
                if not os.path.exists(dest_dir): os.makedirs(dest_dir)
                
                # [核心修复] 使用 PathUtils 清洗文件名 (例如 "What's New?" -> "What_s New_")
                safe_title = PathUtils.sanitize_filename(node.title)
                new_filename = f"{safe_title}-pdf.pdf"
                
                dest_path = os.path.join(dest_dir, new_filename)
                
                if not os.path.exists(dest_path):
                    shutil.copy2(node.source_path, dest_path)
                    
                return None # 返回 None 表示不由 Engine 生成 .md 文件
            except Exception as e:
                self.log(f"⚠️ PDF 复制失败 [{node.title}]: {e}")
                return ""

        # === Abaqus HTML 转换逻辑 ===
        try:
            with open(node.source_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            h1_tag = soup.find('h1')
            header_md = md(str(h1_tag), heading_style="ATX") + "\n\n" if h1_tag else ""
            content_area = soup.find('div', class_='conbody') or soup.find('div', class_='body') or soup.body
            if not content_area: return ""
            
            # 清理噪音
            for junk in content_area.select('script, style, .navheader, .navfooter'): junk.decompose()
            
            # 图片处理
            self._process_abaqus_images(content_area, os.path.dirname(node.source_path), image_out_dir)

            main_md = md(str(content_area), heading_style="ATX", strip=['a'], newline_style="BACKSLASH")
            return header_md + main_md
        except Exception as e:
            return f"Conversion Error: {e}"

    def _process_abaqus_images(self, soup_element, src_dir, graphics_dir):
        """复用图片搬运与公式修复逻辑"""
        for img in soup_element.find_all(['img', 'svg']):
            alt = img.get('alt', '') or (img.title.string if img.title else '')
            if alt and any(c in alt for c in ['=', '\\', '+']):
                img.replace_with(f" ${alt}$ ")
                continue
            src = img.get('src')
            if src and not src.startswith(('http', 'data:')) and graphics_dir:
                abs_src = os.path.normpath(os.path.join(src_dir, src))
                if os.path.exists(abs_src):
                    if not os.path.exists(graphics_dir): os.makedirs(graphics_dir)
                    fname = os.path.basename(abs_src)
                    dst_path = os.path.join(graphics_dir, fname)
                    if not os.path.exists(dst_path):
                        try: shutil.copy2(abs_src, dst_path)
                        except: pass
                    img['src'] = f"assets/{fname}"

    def _parse_child_xml(self, xml_path, parent_node, context_dir, level):
        try:
            parser = ET.XMLParser(recover=True, encoding='utf-8')
            tree = ET.parse(xml_path, parser=parser)
            def _walk_item(element, current_p_node, current_level):
                for i, item in enumerate(element.xpath("./ITEM"), start=1):
                    title = item.get("title")
                    abs_html_path = self._get_abs_path(context_dir, item.get("href"))
                    child_node = DocNode(title=title, level=current_level, index=i, source_path=abs_html_path, 
                                         is_container=len(item.xpath("./ITEM")) > 0)
                    current_p_node.add_child(child_node)
                    if child_node.is_container: _walk_item(item, child_node, current_level + 1)
            _walk_item(tree.getroot(), parent_node, level)
        except: pass

    def _walk_internal_items(self, element, current_p_node, level):
        for i, item in enumerate(element.xpath("./ITEM"), start=1):
            title = item.get("name") or item.get("title")
            child_node = DocNode(title=title, level=level, index=i, source_path=self._get_abs_path("", item.get("href")), 
                                 is_container=True if item.xpath("./ITEM") else False)
            current_p_node.add_child(child_node)
            if child_node.is_container: self._walk_internal_items(item, child_node, level + 1)

    def _get_abs_path(self, context_dir, href):
        if not href: return None
        clean_href = href.split('#')[0]
        abs_path = os.path.normpath(os.path.join(self.src_root, context_dir, clean_href))
        return abs_path if os.path.exists(abs_path) else None

    def process_task(self, task): pass

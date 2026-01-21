import os
import shutil
from bs4 import BeautifulSoup
from markdownify import markdownify as md

class ContentConverter:
    @staticmethod
    def convert_to_string(html_src_path, graphics_dir=None):
        """
        核心逻辑：读取HTML，搬运图片，返回Markdown字符串。
        :param html_src_path: HTML 源文件路径
        :param graphics_dir: 图片输出目录 (如果为None，则不搬运图片)
        :return: 转换后的 Markdown 字符串
        """
        if not os.path.exists(html_src_path):
            return ""

        try:
            with open(html_src_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            # 1. 定位正文 (Ansys 常用结构)
            content = soup.find('div', class_='section') or \
                      soup.find('div', class_='chapter') or \
                      soup.find('div', class_='sect1') or \
                      soup.body
            if not content: return ""

            # 2. 图片处理 & 公式修复
            src_dir = os.path.dirname(html_src_path)
            
            for img in content.find_all(['img', 'svg']):
                # A. 简单的公式修复 (alt 转 LaTeX)
                alt = img.get('alt', '') or (img.title.string if img.title else '')
                if alt and any(c in alt for c in ['=', '\\', '+']):
                    img.replace_with(f" ${alt}$ ")
                    continue
                
                # B. 图片搬运
                src = img.get('src')
                if src and not src.startswith(('http', 'data:')) and graphics_dir:
                    abs_src = os.path.normpath(os.path.join(src_dir, src))
                    if os.path.exists(abs_src):
                        if not os.path.exists(graphics_dir):
                            os.makedirs(graphics_dir)
                        
                        fname = os.path.basename(abs_src)
                        dst_path = os.path.join(graphics_dir, fname)
                        
                        # 复制文件 (避免重复复制可加判断)
                        if not os.path.exists(dst_path):
                            try: shutil.copy2(abs_src, dst_path)
                            except: pass
                        
                        # 修改 Markdown 里的链接
                        img['src'] = f"assets/{fname}"

            # 3. 噪音清洗
            for junk in content.select('script, style, .navheader, .navfooter'):
                junk.decompose()

            # 4. 生成 Markdown
            return md(str(content), heading_style="ATX", strip=['a'], newline_style="BACKSLASH")

        except Exception as e:
            return f"Conversion Error: {e}"

    @staticmethod
    def convert_file(html_src_path, md_dst_path):
        """
        兼容旧接口：直接文件对文件转换 (File-to-File)
        """
        # 自动计算图片目录: output/graphics
        md_dir = os.path.dirname(md_dst_path)
        graphics_dir = os.path.join(md_dir, "graphics")
        
        # 调用核心逻辑
        md_text = ContentConverter.convert_to_string(html_src_path, graphics_dir)
        
        # 写入文件
        if md_text:
            if not os.path.exists(md_dir): os.makedirs(md_dir)
            with open(md_dst_path, 'w', encoding='utf-8') as f:
                f.write(md_text)
            return True
        return False

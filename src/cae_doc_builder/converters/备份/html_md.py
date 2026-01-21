import os
import shutil
from bs4 import BeautifulSoup
from markdownify import markdownify as md

class ContentConverter:
    @staticmethod
    def convert_file(html_src_path, md_dst_path):
        try:
            with open(html_src_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            content = soup.find('div', class_='section') or \
                      soup.find('div', class_='chapter') or \
                      soup.find('div', class_='sect1') or \
                      soup.body
            if not content: return False

            md_dir = os.path.dirname(md_dst_path)
            if not os.path.exists(md_dir): os.makedirs(md_dir)
            graphics_dir = os.path.join(md_dir, "graphics")
            src_dir = os.path.dirname(html_src_path)

            for img in content.find_all(['img', 'svg']):
                alt = img.get('alt', '') or (img.title.string if img.title else '')
                if alt and any(c in alt for c in ['=', '\\', '+']):
                    img.replace_with(f" ${alt}$ ")
                    continue
                src = img.get('src')
                if src and not src.startswith(('http', 'data:')):
                    abs_src = os.path.join(src_dir, src)
                    if os.path.exists(abs_src):
                        if not os.path.exists(graphics_dir): os.makedirs(graphics_dir)
                        fname = os.path.basename(abs_src)
                        shutil.copy2(abs_src, os.path.join(graphics_dir, fname))
                        img['src'] = f"graphics/{fname}"

            for junk in content.select('script, style, .navheader, .navfooter'):
                junk.decompose()

            md_text = md(str(content), heading_style="ATX", strip=['a'], newline_style="BACKSLASH")
            with open(md_dst_path, 'w', encoding='utf-8') as f:
                f.write(md_text)
            return True
        except: return False

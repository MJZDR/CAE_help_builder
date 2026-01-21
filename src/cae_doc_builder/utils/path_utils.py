import re

class PathUtils:
    @staticmethod
    def sanitize_filename(name):
        # 1. 替换换行、回车、制表符为空格
        name = re.sub(r'[\r\n\t]+', ' ', name)
        # 2. 移除非法字符
        name = re.sub(r'[\\/*?:"<>|]', '_', name)
        # 3. 合并多余空格
        name = re.sub(r'\s+', ' ', name)
        return name.strip().rstrip('.')

    @staticmethod
    def has_existing_numbering(text):
        return bool(re.match(r'^(\d+\.)+', text))

    @staticmethod
    def generate_name(title, index):
        safe_title = PathUtils.sanitize_filename(title)
        if PathUtils.has_existing_numbering(safe_title):
            return safe_title
        else:
            return f"{index}-{safe_title}"

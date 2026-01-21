from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    def __init__(self, src_root, out_root, logger_func):
        self.src_root = src_root
        self.out_root = out_root
        self.log = logger_func

    @abstractmethod
    def process_task(self, task):
        """处理单个构建任务"""
        pass

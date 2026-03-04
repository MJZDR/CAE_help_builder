from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class DocNode:
    """
    通用文档节点：锁定 index 确保编号稳定
    """
    title: str                      # 节点标题
    level: int                      # 层级深度
    index: int = 0                  # [新增] 扫描时的原始物理序号
    source_path: Optional[str] = None  # 源文件路径
    children: List['DocNode'] = field(default_factory=list) 
    is_container: bool = False      # 是否为文件夹
    
    def add_child(self, node: 'DocNode'):
        self.children.append(node)

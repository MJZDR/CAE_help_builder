from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class DocNode:
    title: str                      # 节点标题
    level: int                      # 层级深度
    index: int = 0                  # [新增] 扫描时的原始序号
    source_path: Optional[str] = None  
    target_filename: Optional[str] = None 
    children: List['DocNode'] = field(default_factory=list) 
    is_container: bool = False      
    
    def add_child(self, node: 'DocNode'):
        self.children.append(node)

    def __repr__(self):
        return f"<DocNode(title='{self.title}', children={len(self.children)}, index={self.index})>"

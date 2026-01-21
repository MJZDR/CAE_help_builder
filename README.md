CAE Documentation to Markdown Knowledge Base Builder

📖 项目简介 (Introduction)

本项目是一个通用的 CAE 软件（Ansys, ANSA, Abaqus）帮助文档转换工具。它旨在将传统的、结构复杂的本地离线帮助文档（HTML/XML/PDF）转换为结构清晰、对 AI 友好且易于笔记管理的 **Markdown 知识库**。

项目已从单一脚本重构为 **Python 包 (`cae_doc_builder`)**，采用**适配器模式 (Adapter Pattern)** 设计，实现了核心逻辑与具体软件解析的分离，具备极强的扩展性。

**当前版本**: V1.0 (支持 ANSA, Ansys, Abaqus)🏗️ 项目架构与模块功能 (Architecture & Modules)

* * *

项目采用模块化设计，核心代码位于 `src/` 目录下，各模块分工明确：

文件结构：

    Project_Root/
    │
    ├── main_gui.py                    # [入口] GUI 启动脚本
    ├── run_builder.bat                # [入口] Windows 一键启动批处理
    ├── setup.py                       # 包安装配置文件
    ├── README.md                      # 项目文档
    │
    └── src/
        └── cae_doc_builder/           # 核心 Python 包
            ├── __init__.py
            ├── core/                  # 核心引擎层
            │   ├── engine.py          # 构建流程控制器
            │   └── structures.py      # 通用数据结构 (DocNode)
            │
            ├── adapters/              # 适配器层 (扩展核心)
            │   ├── base.py            # 适配器基类接口
            │   └── ansys_adapter.py   # Ansys 专用解析逻辑
            │
            ├── converters/            # 转换层
            │   └── html_md.py         # HTML -> Markdown 转换器
            │
            └── utils/                 # 工具层
                └── path_utils.py      # 路径清洗与命名工具

### 1. 核心层 (`src/cae_doc_builder/core/`)

* **`engine.py` (构建引擎)**:
  
  * **职责**: 项目的总指挥。负责接收适配器生成的“文档树 (`DocNode` Tree)”，并递归地在硬盘上创建对应的文件夹结构。
    
  * **特性**: 实现了**自动编号**（基于扫描时的物理顺序）、**防重复构建**（自动剔除被父节点包含的子节点任务）、**资源搬运**（Markdown 写入与图片/PDF 存储）。
    
* **`structures.py` (数据结构)**:
  
  * **职责**: 定义了通用的 `DocNode` 类。
    
  * **特性**: 包含 `title` (标题), `level` (层级), `source_path` (源文件路径), `index` (物理序号)。所有不同软件的文档结构最终都被标准化为这种格式。
    

### 2. 适配器层 (`src/cae_doc_builder/adapters/`)

* **`base.py`**: 定义适配器的标准接口（`parse_structure` 和 `read_file_content`）。
  
* **具体适配器**: 详见下文“适配器特性”章节。
  

### 3. 转换与工具层 (`src/cae_doc_builder/converters/` & `utils/`)

* **`html_md.py`**:
  
  * **职责**: 通用的 HTML 到 Markdown 转换器。
    
  * **特性**: 基于 `BeautifulSoup` 和 `markdownify`。自动提取正文、清洗导航栏噪音、将 HTML 图片标签转换为 Markdown 本地链接，并修复公式格式。
    
* **`path_utils.py`**:
  
  * **职责**: 路径安全卫士。
    
  * **特性**: 提供了 `sanitize_filename` 方法，强制替换 Windows 非法字符（`?`, `/`, `:`, `*` 等），并负责生成形如 `01-Introduction` 的有序文件名。
    

🧩 三大适配器特性与索引结构解析 (Adapters & Indexing)

不同的 CAE 软件采用完全不同的方式组织其帮助文档。本项目针对每种软件实现了定制化的解析逻辑。

### 1. ANSYS Adapter

* **索引结构**: **集中式 XML 索引**。
  
  * 入口文件通常位于 `.../commonfiles/help/en-us/toc_config.xml`。
    
  * 结构逻辑：`toc_config.xml` 定义顶层的 **Set (集合)** 和 **Book (书籍)**，每本书指向一个独立的子目录（如 `wb2_help`），其内部通过 `toc.toc` 文件定义具体的章节树。
    
* **适配器特性**:
  
  * **双层解析**: 先解析主 XML 获取书架，再按需递归解析书籍内部的 `toc.toc` (HTML 列表)。
    
  * **通用转换**: 使用标准的 `html_md.py` 进行内容转换。
    

### 2. ANSA Adapter

* **索引结构**: **物理文件系统索引**。
  
  * ANSA 文档通常直接以文件夹层级存储在 `docs/` 目录下。
    
  * 结构逻辑：**文件夹 = 章节**，文件夹下的 `index.html` = 章节内容。
    
* **适配器特性**:
  
  * **物理扫描**: 直接利用 `os.listdir` 扫描物理目录结构。
    
  * **专用清洗**: 针对 ANSA 使用的 Sphinx/Furo 主题进行了深度优化，自动剔除侧边栏、面包屑导航、API 索引等特定噪音。
    
  * **虚拟节点**: 能处理只有子文件夹但没有 `index.html` 的“纯容器”节点。
    

### 3. ABAQUS Adapter (V3.1 新增)

* **索引结构**: **分布式 XML 索引**。
  
  * 入口文件通常为 `.../English/DSSIMULIA_Established_TOC.xml`。
    
  * 结构逻辑：主 XML 定义模块 (Module) 和书籍 (Book)。每一本书籍通过 `childtoc` 属性指向其子文件夹下的 `structure.xml`，形成多级嵌套。
    
* **适配器特性**:
  
  * **混合资源处理**:
    
    * **HTML**: 针对 Abaqus 特有的“多 Section 平铺”结构，重写了内容抓取逻辑，确保不丢失正文后的列表和参考链接。
      
    * **PDF**: 自动识别 `fe-safe` 等模块下的 PDF 资源。**不进行转换**，而是执行物理复制，并自动清洗文件名（去除 `?` 等非法字符）。
      
  * **递归 XML**: 支持无限层级的 `structure.xml` 递归解析。
    

✨ 核心功能 (Features)

* **全自动层级解析**: 完美还原软件原始目录树，支持无限层级。
  
* **稳定有序**: 无论勾选顺序如何，生成的文件始终保持原始文档的物理编号 (Index)。
  
* **多模态支持**:
  
  * **HTML**: 转为 Markdown，保留图片、公式、表格。
    
  * **PDF**: 自动识别并原样搬运。
    
* **智能清洗**: 强制修复 Windows 文件名兼容性问题，自动去噪。
  
* **GUI 交互**: 提供树状目录选择、多任务并发、实时日志反馈、自动去重（勾选父节点自动忽略子节点任务）。
  

🚀 安装与运行 (Installation & Usage)

### 方法一：Windows 一键启动 (推荐)

直接双击项目根目录下的 **`run_builder.bat`**。

### 方法二：手动运行

Bash pip install -e . python main_gui.py

### 操作指南

1. **选择类型**: 在 GUI 左上角选择对应的软件类型 (ANSA / ANSYS / ABAQUS)。
  
2. **配置源目录**:
  
  * **ANSYS**: 指向 `.../help/en-us` (包含 `toc_config.xml` 的目录)。
    
  * **ANSA**: 指向文档根目录 (包含众多子文件夹的目录)。
    
  * **ABAQUS**: 指向 `.../English` (包含 `DSSIMULIA_Established_TOC.xml` 的目录)。
    
3. **加载结构**: 点击“加载目录结构”，等待解析完成。
  
4. **构建**: 勾选需要的章节（支持多选），点击“构建选中项”。
  

🛠️ 环境依赖 (Requirements)

* Python 3.x
  
* `beautifulsoup4`
  
* `lxml`
  
* `markdownify`
  
* `tkinter` (内置)
  

* * *

**Version**: V1.0

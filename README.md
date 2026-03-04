CAE Documentation to Markdown Knowledge Base Builder
====================================================

📖 项目简介 (Introduction)
----------------------



**注：本项目大部分代码由AI编写，本是私人使用，不具有普适性。但如果能给你带来灵感，也可自行修改优化使用。**



本项目是一个通用的 CAE 软件（Ansys, ANSA, Abaqus）帮助文档转换工具。它旨在将传统的、结构复杂的本地离线帮助文档（HTML/XML/PDF）转换为结构清晰、对 AI 友好且易于笔记管理的 **Markdown 知识库**。

项目已从单一脚本重构为 **Python 包 (`cae_doc_builder`)**，采用**适配器模式 (Adapter Pattern)** 设计，实现了核心逻辑与具体软件解析的分离，具备极强的扩展性。

**当前版本**: V3.1 (由于本人手头上版本少，目前仅支持 ANSA25.0.0, Ansys2024R2, Abaqus2025)

🏗️ 项目架构与模块功能 (Architecture & Modules)

--------------------------------------

项目采用模块化设计，核心代码位于 `src/` 目录下，各模块分工明确：

文件结构：

```
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
```

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

🏗️ CAE 帮助文档架构与提取要点 (Deep Dive)
-------------------------------

### 1. ANSA: 物理路径驱动型 (Physical File System)

ANSA 的帮助文档通常是典型的 **Sphinx** 静态网页，其结构主要由操作系统的文件夹层级决定。

* **文档结构**:
  
  * **索引方式**: 物理目录扫描。
  
  * **层级逻辑**: 文件夹 = 目录节点 (Container)；文件夹下的 `index.html` = 该目录的介绍页；其他 `.html` = 具体章节。

* **页面结构与噪音**:
  
  * 使用 Furo 或经典 Sphinx 主题，页面左右两侧通常有固定的导航栏（Sidebar）和搜索框。

* **提取要点**:
  
  * **正文定位**: 优先寻找 `div[role=main]` 或 `div[itemprop=articleBody]`。
  
  * **标题提取**: 从 `<title>` 中提取并利用正则切除类似 `— ANSA documentation` 的后缀。
  
  * **噪音清洗**: 必须移除 `div.sphinxsidebar`、`footer`、`div.related` 以及侧边栏容器 `aside`。

* * *

### 2. Ansys: 集中配置与 ID 锚点型 (Centralized XML & Anchors)

Ansys 的文档体系最为复杂，采用类似 **DITA** 的结构，利用 XML 配置文件来动态映射物理文件。

* **文档结构**:
  
  * **一级索引**: `toc_config.xml`。定义了 **Set (集合)** 和 **Book (书籍)**。
  
  * **二级索引**: 每本书目录下的 `toc.toc`。它使用 `<title>` 定义书名，使用嵌套的 `<a>` 标签定义章节。
  
  * **层级逻辑**: 通过 `dt` (定义标题) 和紧随其后的 `dd` (定义子容器) 的同级关系来还原嵌套树。

* **页面结构与去重**:
  
  * **文件共用**: 深层章节（如 Release Notes）经常出现多个目录项指向同一个 `.html` 文件的不同 `#锚点`。

* **提取要点**:
  
  * **标题优先级**: 优先读取 `toc.toc` 中 `title` 标签的 `title2` 属性，这通常是真正的人话标题。
  
  * **去重逻辑**: 在解析 `toc.toc` 时，必须切除 `href` 的 `#` 锚点部分。如果连续多个条目指向同一个物理文件，**仅生成一个 DocNode**，防止生成大量内容完全重复的 Markdown。
  
  * **容器命名**: 如果文件夹有内容，介绍页应命名为“标题.md”并置于文件夹内。

* * *

### 3. Abaqus: 分布式 XML 索引型 (Distributed XML Mapping)

Abaqus (Dassault Systemes) 采用分布式 XML 映射，数据与展示层级高度分离。

* **文档结构**:
  
  * **总表**: `DSSIMULIA_Established_TOC.xml`。
  
  * **书籍索引**: 每个模块通过 `childtoc` 属性指向其目录下的 `structure.xml`。
  
  * **混合资源**: 同时包含 HTML 和 PDF 书籍。

* **页面结构与提取**:
  
  * Abaqus 的 HTML 页面通常非常扁平，正文由多个平级的 `div.section` 组成，整体包裹在 `conbody` 容器中。

* **提取要点**:
  
  * **全量抓取**: 传统的 `find('div', class_='section')` 会因为只抓取第一个匹配项而导致内容丢失。必须优先定位 `div.conbody` 或 `div.body` 来抓取所有内容块。
  
  * **标题补偿**: Abaqus 的标题 `<h1>` 往往在正文容器之外（例如在 `DocHeader` 表格中），提取时需要手动抓取并拼接到 Markdown 头部。
  
  * **PDF 审计**: 扫描阶段需记录 `href` 以 `.pdf` 结尾的项，并在构建阶段直接执行物理复制，同时对标题进行 Windows 文件名安全清洗。

* * *

### 🛠️ 通用优化与扩展原则

1. **固定编号 (Fixed Index)**:
   
   * 所有适配器在 `parse_structure` 阶段必须使用 `enumerate` 为 `DocNode.index` 赋值。
   
   * `Engine` 在构建时会依据该 `index` 强制生成有序文件名，确保知识库目录不乱序。

2. **安全命名 (Sanitize)**:
   
   * 无论原始标题包含 `?`、`/` 还是 `:`，在写入磁盘前必须调用 `PathUtils.sanitize_filename`。

3. **资源管理 (Assets)**:
   
   * 图片和附件统一存放在当前层级的 `assets/` 文件夹下，保持知识库的可迁移性。

4. **去重逻辑 (Deduplication)**:
   
   * 在 GUI 启动构建前，必须执行“祖先检查”，即如果父文件夹已被勾选，则其下的子任务自动忽略，由父文件夹的递归逻辑统一处理

✨ 核心功能 (Features)
-----------------

* **全自动层级解析**: 完美还原软件原始目录树，支持无限层级。

* **稳定有序**: 无论勾选顺序如何，生成的文件始终保持原始文档的物理编号 (Index)。

* **多模态支持**:
  
  * **HTML**: 转为 Markdown，保留图片、公式、表格。
  
  * **PDF**: 自动识别并原样搬运。

* **智能清洗**: 强制修复 Windows 文件名兼容性问题，自动去噪。

* **GUI 交互**: 提供树状目录选择、多任务并发、实时日志反馈、自动去重（勾选父节点自动忽略子节点任务）。

🚀 安装与运行 (Installation & Usage)
-------------------------------

### 方法一：Windows 一键启动 (推荐)

直接双击项目根目录下的 **`run_builder.bat`**。

### 方法二：手动运行

Bash
    pip install -e .
    python main_gui.py

### 操作指南

1. **选择类型**: 在 GUI 左上角选择对应的软件类型 (ANSA / ANSYS / ABAQUS)。

2. **配置源目录**:
   
   * **ANSYS**: 指向 `.../help/en-us` (包含 `toc_config.xml` 的目录)。
   
   * **ANSA**: 指向文档根目录 (包含众多子文件夹的目录)。
   
   * **ABAQUS**: 指向 `.../English` (包含 `DSSIMULIA_Established_TOC.xml` 的目录)。

3. **加载结构**: 点击“加载目录结构”，等待解析完成。

4. **构建**: 勾选需要的章节（支持多选），点击“构建选中项”。

🛠️ 环境依赖 (Requirements)
-----------------------

* Python 3.x

* `beautifulsoup4`

* `lxml`

* `markdownify`

* `tkinter` (内置)

* * *

**Version**: V3.1

目前已经导出一版，暂时没发现什么问题：
通过网盘分享的文件：CAE_Knowledge_Base.7z
链接: https://pan.baidu.com/s/1uUx0Vq_sZRJF6cDq_aliLw?pwd=8cdb 提取码: 8cdb 

# RAGLearn 当前状态

更新：2026-10-27（Asia/Shanghai）。单一学习路线；长期规则见 [AGENTS.md](AGENTS.md)。

## 当前阶段与下一步

用户已报告完成 NumPy 版向量化与检索。现在学习 Chroma 本地持久化；用户自己安装、写脚本和运行。助手已建立项目规范、学习笔记和完整教程，并按用户要求将阅读文档归入 docs/；根目录保留 Agent 工作文档。

下一步：用户按 [CHROMA_GUIDE.md](docs/CHROMA_GUIDE.md) 从安装 Chroma 开始，先将现有 index/ 快照导入新 collection，再按阶段验收。新 session 不要自动执行教程。

## 当前证据

- 只读检查：build_index.py、search.py、ask.py 已存在；ask.py 已使用 Codex CLI。未执行模型推理或问答。
- index/metadata.json：模型 BAAI/bge-small-zh-v1.5，3 个 chunk；来源为 equipment.txt、lab_rules.txt、network.txt。
- index/embeddings.npy：形状 (3, 512)，float32，值有限，行范数约为 1。这只证明存储结构/数值检查通过。
- .venv 中查得 numpy 2.5.4、sentence-transformers 6.1.0；chromadb 未安装。这是本轮检查的版本，后续可能变化。
- 用户报告基础 embedding 与找回原 chunk 成功；不由此推定 Codex 回答或 Chroma 已验收。
- 已核对 Chroma 官方 PersistentClient、显式 embedding、cosine 配置、get/query/upsert/delete 用法；教程代码仅静态检查，未安装 Chroma、未创建数据库、未执行示例。
- 文档验证：7 个 Python 代码块通过 AST 语法解析，其中 4 个是完整参考脚本；4 份文档的本地链接与代码围栏检查通过，git diff --check 通过。确认未落地教程脚本或 chroma_db/，已有 tracked 文件无变更。
- 先前 session 曾检查 Codex CLI 0.162.1、ChatGPT 登录；本轮没有重新核实 CLI/账号，不宣称仍是当前状态。

## 已有用户文件与已知问题

- 基线脚本、data/、index/ 和 _temp/ 原样保留。
- 初始 Git 状态：已有未跟踪 _temp/；无 tracked diff。本轮不检查其内容、不清理、不提交。
- build_index.py 的后缀集合是 {'.txt', 'md'}，会跳过 .md；接入 Markdown 时由用户改成 {'.txt', '.md'}。助手未改代码。
- 当前 .gitattributes 包含项目虚拟环境内一个 torch DLL 的 LFS 规则；本轮未调整 Git/环境文件。

## 技术决策

- 本轮先复用现有向量快照学习数据库，避免同时改变模型、切块与语料。
- Chroma 本地目录拟用 chroma_db/，collection 拟用 rag_learning_v1；第一次 import 使用 create_collection，已存在时停止，防止静默覆盖。重新导入使用用户明确指定的新 collection 名。
- 显式传入向量，embedding_function=None；cosine 距离，检索端 score = 1 - distance，保留现有 retrieve() 返回字段。
- 另建 ask_chroma.py，仅将检索导入改到 search_chroma；保留原版作为对照。
- CRUD 使用独立 rag_learning_crud collection，只改动教程生成的 lesson-demo 记录；不删除基线或学习主 collection。
- Markdown 和个人 Obsidian 是后续阶段；未读取、枚举、复制或索引 Vault。个人笔记接入与云端发送范围需要届时明确授权。

## 文档入口

- [LEARNING_NOTES.md](docs/LEARNING_NOTES.md)：已问问题、数据关系、目录层级与文件作用。
- [CHROMA_GUIDE.md](docs/CHROMA_GUIDE.md)：全流程、参考代码、命令、错误排查与验收表。

## 待验收（均未运行）

1. 用户安装 Chroma，记录实际版本；依赖失败先读具体错误，不盲目升级全部环境。
2. 导入 3 条记录；按 ID 检查文本、来源和向量维度。
3. 检索与来源过滤，和 NumPy 结果逐项对照；处理距离方向与近似检索差异。
4. 退出进程再读取，验证持久化；执行独立 CRUD 练习并确认主 collection 数量不变。
5. Codex 连接与数据库版问答，核对答案、引用和语料外拒答；不只看进程退出码。
6. 之后再考虑索引本项目 Markdown 文档，以及明确范围的个人 Obsidian 实验。

当前文档：根目录 AGENTS.md、HANDOFF.md；用户阅读文档 docs/LEARNING_NOTES.md、docs/CHROMA_GUIDE.md。分类后已同步相对链接、目录树和教程复制源路径。未改业务脚本、依赖、索引与 Git 配置，未 commit/push。

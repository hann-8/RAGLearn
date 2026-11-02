# RAG 学习笔记

更新：2026-10-28。当前实操先读 [OBSIDIAN_RAG_V2_GUIDE.md](OBSIDIAN_RAG_V2_GUIDE.md)，设计与样本证据见 [OBSIDIAN_CHUNKING_DESIGN.md](OBSIDIAN_CHUNKING_DESIGN.md)；数据库教程见 [CHROMA_GUIDE.md](CHROMA_GUIDE.md)，v1 对照见 [OBSIDIAN_RAG_GUIDE.md](OBSIDIAN_RAG_GUIDE.md)，完成情况见 [HANDOFF.md](../HANDOFF.md)。这里解释概念，不把尚未运行的步骤写成已完成。

## 1. RAG 的两条流程

```text
准备资料：文档 → 切块 → embedding → 保存原文、来源与向量
回答问题：问题 → embedding → 检索片段 → 组装提示词 → LLM 回答并引用
```

Embedding 模型把文本表示为向量，用于比较相关程度；LLM 根据问题和参考资料组织答案。它们承担不同工作。RAG 通常是在推理时提供上下文，不需要修改 LLM 权重。

## 2. metadata.json 只是方便人看吗？

不是。当前文件同时保存：

| 字段 | 含义 | 程序为什么需要 |
| --- | --- | --- |
| model_name | 向量模型名称 | 查询使用相同模型 |
| query_prefix | 查询前缀 | 保持问题编码方式一致 |
| chunk_size / chunk_overlap | 切块参数 | 记录索引构建方式 |
| chunks[].id | 片段标识 | 定位和引用 |
| chunks[].source | 相对于 data/ 的来源路径 | 返回来源 |
| chunks[].text | 片段原文 | 展示并提供给回答模型 |

严格说 text 是正文，source/id 是记录元数据，模型与切块参数是索引配置。学习版把它们放进一个可读 JSON 文件。

## 3. embeddings.npy 是向量数据库吗？

它只是保存 NumPy 数组的文件。当前是 (3, 512)：3 个 chunk，每个向量 512 个数。512 是本项目当前模型的维度，不是所有 embedding 模型的固定值。

```python
embeddings[i]  # 第 i 个 chunk 的向量
chunks[i]      # 同一个 chunk 的原文、ID 和来源
```

search.py 找到相似向量的行号，再据此取回原文。原文不是从向量中解码还原出来的。

## 4. index/ 是向量索引吗？向量索引属于数据库吗？

当前 index/ 是我们给“检索产物目录”起的名字；里面保存数据，search.py 对全部向量逐一计算后排序，没有额外建立 HNSW 这类专用 ANN 检索结构。

向量是数据；向量索引是组织向量并支持相似检索的数据结构；向量数据库管理记录、持久化、检索与增删改查等能力。向量索引通常是数据库的一部分，也可以被单独的检索库使用，并不要求一定存在数据库服务器。

```text
Chroma 数据库
└── collection（一个数据集合，便于类比一张表，但不等同 SQL 表）
    ├── 记录：ID、document、embedding、metadata
    └── 检索索引及相关内部结构
```

Chroma 本地嵌入式模式是数据库使用方式；不需要为了叫“数据库”就先启动独立服务。[官方架构说明](https://docs.trychroma.com/reference/architecture/overview)

## 5. 相似度、距离和答案正确率

- 归一化向量的点积是余弦相似度，越大越近。
- 本教程显式选择 Chroma cosine：distance = 1 - cosine_similarity，越小越近；展示时可用 score = 1 - distance 对齐 NumPy。
- 这个换算不能直接套在所有其他度量上；浮点误差可能造成边界附近的微小偏差。
- 相似度不是“答案正确的概率”。top_k 总会尽量返回候选，语料外问题也可能拿到看似相关的片段。
- NumPy 基线是全量精确比较；HNSW 是近似检索。比较结果时检查候选、分数和相关性，不预设所有数据规模下完全相同或更快。

距离公式见 [Chroma 配置说明](https://docs.trychroma.com/docs/collections/configure)。

## 6. ask.py 是拼 system prompt、question、references 吗？

整体理解正确：把回答规则、问题、检索到的原文和引用编号组织成模型输入。

当前 Codex CLI 版把它们拼成一次任务 prompt；规则在作用上类似 system prompt，但代码没有单独构造 system 角色消息。提示词要求只根据片段回答、资料不足时说明；它不是技术上禁用所有工具的隔离机制。

当前模型生成调用需要联网，问题与参考片段会发送给 Codex。片段作为本次上下文，不是在训练模型。带引用只是形式，仍须人工检查引用是否支持结论。

## 7. 文本少，有必要引入数据库吗？

以学习为目的值得尝试。收益是理解持久化、ID、集合、过滤、增删改查、索引和数据一致性；当前 3 条文本并不构成性能上必须换数据库的理由。

先保持模型、切块、问题和语料不变，只把存储/检索换成 Chroma。Chroma 的集合管理不等于完整学习了关系型数据库的 SQL、连接和跨表事务。

## 8. 项目目录逐层说明

下表中 import_chroma.py、search_chroma.py、inspect_chroma.py 已由用户创建，2026-10-28 只读检查确认。标记“待创建”的内容仍是教程设计；数据库内部产物没有在本轮检查。

```text
08_RAGLearn/
├── AGENTS.md               长期协作规则和边界
├── HANDOFF.md              当前进度、证据和下一步
├── docs/                  给用户阅读的项目文档
│   ├── LEARNING_NOTES.md   概念与问题总结（本文件）
│   ├── CHROMA_GUIDE.md     数据库版完整操作教程
│   ├── OBSIDIAN_RAG_GUIDE.md 笔记样本 v1 链路与参考代码
│   ├── OBSIDIAN_CHUNKING_DESIGN.md 真实样本审阅与当前 v2 分块设计
│   └── OBSIDIAN_RAG_V2_GUIDE.md 当前完整实操，含增量同步
├── .git/                   Git 自身的历史、对象和索引
├── .gitattributes          Git 属性规则；当前包含一个 torch DLL 的 LFS 规则
├── .venv/                  本项目 Python 环境
│   ├── Scripts/            python.exe、pip 与其他命令入口
│   ├── Lib/site-packages/  已安装的第三方库
│   ├── Include/            扩展编译相关头文件目录
│   ├── share/              依赖附带的共享资源
│   └── pyvenv.cfg          虚拟环境配置
├── data/                   允许本轮索引的原始示例资料
│   ├── equipment.txt       设备说明
│   ├── lab_rules.txt       实验室规定
│   └── network.txt         网络说明
├── index/                  NumPy 版生成的检索快照
│   ├── metadata.json       模型配置、chunk 原文和来源
│   └── embeddings.npy      与 chunks 数组逐行对应的向量矩阵
├── build_index.py          原始资料 → chunk → 向量 → 文件快照
├── search.py               问题向量 → NumPy 全量比较 → 返回 chunk
├── ask.py                  调用 search.retrieve，再交给 Codex 回答
├── _temp/                  用户已有临时目录，内容未检查，不自动清理
├── import_chroma.py        已存在：把现有快照导入 Chroma
├── search_chroma.py        已存在：Chroma 相似检索及来源过滤
├── inspect_chroma.py       已存在：数量、按 ID 读取、查看向量维度
├── crud_chroma.py          待创建：独立集合中的增删改查练习
├── ask_chroma.py           待创建：原 ask.py 的数据库检索版本
└── chroma_db/              用户报告已建库；本轮未检查内部文件
```

根目录的 AGENTS.md、HANDOFF.md 用于 Agent 工作和跨 session 交接；docs/ 集中放用户阅读的教程、笔记和说明。`data/` 是原始输入；`index/` 和 `chroma_db/` 是派生存储。不要把数据库目录放进 data/，也不要手动改数据库内部文件。

Chroma 可能在 chroma_db/ 下创建 SQLite 文件、索引子目录等内部产物；具体文件布局由安装版本管理，不把某个布局写成永久契约。集合的逻辑名称不保证等于磁盘子目录名称。

项目 .git/ 内部也有一个叫 index 的文件，那是 Git 的暂存区索引，与项目根目录的 index/、RAG 向量索引无关。

## 9. 模型配置、重复导入和更新

- embedding_function=None 表示本实验不让 Chroma 自动选择向量模型；写入传 embeddings，检索传 query_embeddings。
- collection 的 metadata 保存模型名、查询前缀和切块参数；每条记录的 metadata 保存来源。它们是两个层级。
- ID 解决记录身份和对应关系；模型不一致时，即使维度相同，也不能混合比较。
- add 新增，get 按 ID/条件取记录，query 按相似度检索，update 更新已有记录，upsert 有则更新无则新增，delete 删除指定记录。
- 改正文必须重算该正文的向量；只改 source 等元数据通常不需要重算正文向量。
- upsert 不会自动删掉已经从原资料消失的 chunk；删文档、改切块后需要明确清理或重建策略。
- 本轮 import 在 collection 已存在时停止。重新导入先选新版本集合名，保留旧结果供核对。

## 10. Obsidian 小样本实战

用户报告已完成 Chroma 建库、迁移向量、连接、查询与返回 hits，认可基础数据库阶段结束。现在进入笔记实战教学；实际效果仍由用户运行验收。

教程初稿没有读取 Vault；经用户明确要求，先读过 3 个样本，随后按“多看真实样本并记录”的要求又审阅 43 个不同文件（26 个全文、17 个局部，含 4 处中段补读）。允许范围的元数据计数为 325 篇，其中日记 129 篇；不能据此宣称全库正文都已检查。完整证据范围、设计依据和验收案例见 [OBSIDIAN_CHUNKING_DESIGN.md](OBSIDIAN_CHUNKING_DESIGN.md)。源笔记未改写，未复制或向量化笔记，未建库。

v1 流程见 [OBSIDIAN_RAG_GUIDE.md](OBSIDIAN_RAG_GUIDE.md)：用户手选 Markdown 副本 → 程序自动分块和预览 → 沿用现有 CPU 模型 → 独立 Chroma 集合 → 向量与精确关键词搜索 → 真实查询记录 → 可选云端问答。四个完整脚本仍仅是文档中的参考代码；它们未实现当前 v2 设计，不应直接视为全库方案。

当前完整操作入口已更新为 [OBSIDIAN_RAG_V2_GUIDE.md](OBSIDIAN_RAG_V2_GUIDE.md)：五脚本参考实现，包括解析、快照、同步、搜索和可选问答。用户提出频繁新增笔记后，日常改为 prepare + sync，同一 collection 复用未变向量并清除消失的记录；位置/父关联变化只更新 metadata。搜索绑定数据库已成功提交的快照，中断同步禁止查询。模型/解析器变化另建集合。21 项合成/替身检查通过，真实样本、CPU 和数据库仍待用户运行；没有把脚本落到项目根。

- 分块不要求人工逐篇整理，用户只抽查。v2 首选：识别 Markdown/HTML 与噪声 → 生成可检索文本视图 → 按理解依赖组成局部单元 → 生成子块 → 命中后回取必要上下文。不是只把固定长度换成另一个数值。
- 实际样本还包括空模板、占位、纯链接、长 URL、异常围栏、代码语言误标、整页 HTML、任务、表格和粘贴对话。无法处理的内容明确报告，不静默丢失；纯链接/截图不代表目标内容已索引。
- “正确/错误/解释”“前提/现象/结论”和任务父子项需要关联；通用日记标题不意味着同一主题。长代码可尝试结构解析，失败降级，不执行或改写。
- 检索视图清理之后需要源范围映射；不能再假定清洗文本是原文一个连续切片。样本中出现敏感字段，documents、父上下文、预览和发送文本也要同样处理，不只清理 embedding 输入。
- CPU 模型暂不更换。先分开测加载、建库、持续查询与内存；候选模型只有实测性能、效果值得时才替换。
- 原文和问题无需一问一答配对：一个问题可能需要多篇笔记，一篇笔记也能支持多个问题。少量已知原文用于查找验收，未知答案的问题先评价结果是否有用，不能据此证明完整召回或全库没有答案。
- 关键词、标签/日期过滤与向量检索互补。第一版只实现正文子串搜索与向量搜索两个入口，没有自动混合排名、标签解析或时间推理。
- 来源范围、文件哈希与 ID 关联到快照。v2 日常新增/修改/删除使用新快照并同步同一集合，显式删除消失 ID，复用不变向量；更换模型或解析规则才另建集合。属于用户选定范围的手动同步，不是自动全库服务。
- 本地检索与发送原文是不同范围。教程问答脚本默认预览，加显式开关才调用 Codex；不编辑或写回 Vault，也不代表技术上完全隔离了其他工具。

## 后续笔记维护方式

用户提出新疑问并要求记录时，把可复用结论加入对应小节；实际操作结果写 HANDOFF.md。保留来源与适用条件，不堆叠流水账，不将尚未验证的推测写成事实。

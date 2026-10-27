# RAG 学习笔记

更新：2026-10-27。操作教程见 [CHROMA_GUIDE.md](CHROMA_GUIDE.md)，当前完成情况见 [HANDOFF.md](../HANDOFF.md)。这里解释概念，不把尚未运行的步骤写成已完成。

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

标记“待创建”的内容仅存在于教程设计中，助手没有替用户创建对应脚本或数据库。

```text
08_RAGLearn/
├── AGENTS.md               长期协作规则和边界
├── HANDOFF.md              当前进度、证据和下一步
├── docs/                  给用户阅读的项目文档
│   ├── LEARNING_NOTES.md   概念与问题总结（本文件）
│   └── CHROMA_GUIDE.md     数据库版完整操作教程
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
├── import_chroma.py        待创建：把现有快照导入 Chroma
├── search_chroma.py        待创建：Chroma 相似检索及来源过滤
├── inspect_chroma.py       待创建：数量、按 ID 读取、查看向量维度
├── crud_chroma.py          待创建：独立集合中的增删改查练习
├── ask_chroma.py           待创建：原 ask.py 的数据库检索版本
└── chroma_db/              待生成：Chroma 管理的本地数据库文件
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

## 10. 以后接入 Obsidian 前需要决定什么

以后要实际用自己的笔记，并不等于现在授权扫描 Vault。本轮未访问 Vault。

届时先明确允许的笔记子目录、排除目录和文件类型，再设计 Markdown 标题、行号、正文清洗、wikilink、嵌入内容、长段落和增量更新的处理。先用一小批明确选择的副本验证，不默认全库导入。

另行明确是否允许把选中的笔记片段交给云端 Codex；本地向量化和发送原文是不同的数据处理范围。检索不授权编辑或自动写回笔记。

## 后续笔记维护方式

用户提出新疑问并要求记录时，把可复用结论加入对应小节；实际操作结果写 HANDOFF.md。保留来源与适用条件，不堆叠流水账，不将尚未验证的推测写成事实。

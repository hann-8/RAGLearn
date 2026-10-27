# 从 NumPy 检索到 Chroma：完整动手流程

编写日期：2026-10-27。操作由用户执行，助手只提供文档与参考代码。下面的 Python 代码尚未在本机执行 Chroma 运行验收；不要把文档存在理解为数据库已接通。

本轮从已经存在的 3 条示例 chunk 和归一化向量出发。保留原来的 build_index.py、search.py、ask.py 和 index/，另建数据库版。概念和目录说明见 [LEARNING_NOTES.md](LEARNING_NOTES.md)，协作规则见 [AGENTS.md](../AGENTS.md)。本教程位于 docs/，以下命令仍在项目根目录执行。

## 0. 目标与路线

```text
现有 data/ → build_index.py → index/metadata.json + embeddings.npy
                                      ↓ 本轮复用这批向量
                              import_chroma.py
                                      ↓
                     chroma_db/ 中的 rag_learning_v1 集合
                                      ↓
问题 → 同一个 embedding 模型 → search_chroma.py → 相关 chunk
                                      ↓
                              ask_chroma.py → Codex 回答
```

第一轮只改变存储与检索，不同时改变模型、切块和语料。Chroma PersistentClient 是嵌入式本地数据库方式，数据落盘，不要求先部署独立服务器。[官方客户端说明](https://docs.trychroma.com/reference/python/client)

最终要验证：记录数正确、按 ID 可读、相似检索正确、来源过滤有效、进程退出后数据仍存在、增删改只影响演示集合、回答和引用有依据。

## 1. 检查环境并记录 NumPy 基线

所有命令均在 PowerShell 执行：

```powershell
cd C:\ttchina\06_Gitlab\08_RAGLearn

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show numpy sentence-transformers

.\.venv\Scripts\python.exe .\search.py "预约实验室需要提前多久？"
.\.venv\Scripts\python.exe .\search.py "设备坏了，需要提供什么信息？"
```

记下检索到的 ID、原文、来源和分数，后面使用同样的问题比较。现有 index/ 已存在，这一步不需要重跑 build_index.py，也不重新生成向量。

## 2. 安装 Chroma

```powershell
.\.venv\Scripts\python.exe -m pip install chromadb
.\.venv\Scripts\python.exe -m pip show chromadb
```

本教程使用支持 configuration 参数的 Chroma 接口。若安装或调用报错，保留具体版本和原始错误；先核对原因，不直接升级/降级全部环境，也不混用网上旧版 hnsw:space 写法。

安装后重跑一次上一步的 NumPy 检索，确认原版仍能运行。这里不需要额外安装回答模型 SDK，不需要配置新的 API Key。

## 3. 把现有向量导入数据库

在项目根目录手动新建 import_chroma.py：

```python
import argparse
import json
from pathlib import Path

import chromadb
import numpy as np


ROOT = Path(__file__).resolve().parent
INDEX_DIR = ROOT / "index"
DB_DIR = ROOT / "chroma_db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="rag_learning_v1")
    args = parser.parse_args()

    snapshot = json.loads(
        (INDEX_DIR / "metadata.json").read_text(encoding="utf-8")
    )
    vectors = np.load(INDEX_DIR / "embeddings.npy", allow_pickle=False)
    chunks = snapshot["chunks"]
    ids = [chunk["id"] for chunk in chunks]

    if not chunks:
        raise SystemExit("快照没有 chunk，请检查 index/。")
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise SystemExit("chunk 数量与向量矩阵不对应，停止导入。")
    if len(set(ids)) != len(ids):
        raise SystemExit("快照包含重复 ID，停止导入。")
    if not np.isfinite(vectors).all():
        raise SystemExit("向量包含非有限值，停止导入。")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
        raise SystemExit("本教程要求归一化向量，请检查原索引构建方式。")

    client = chromadb.PersistentClient(path=str(DB_DIR))

    # 已存在时会报错；不静默复用，更不自动删除旧集合。
    collection = client.create_collection(
        name=args.collection,
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={
            "model_name": snapshot["model_name"],
            "query_prefix": snapshot["query_prefix"],
            "chunk_size": snapshot["chunk_size"],
            "chunk_overlap": snapshot["chunk_overlap"],
            "normalized": True,
            "metric": "cosine",
        },
    )

    collection.add(
        ids=ids,
        documents=[chunk["text"] for chunk in chunks],
        embeddings=vectors.tolist(),
        metadatas=[{"source": chunk["source"]} for chunk in chunks],
    )

    if collection.count() != len(chunks):
        raise SystemExit("导入后数量不符，请检查数据库内容。")

    print(f"数据库目录：{DB_DIR}")
    print(f"集合：{collection.name}")
    print(f"记录数量：{collection.count()}")
    print(f"向量维度：{vectors.shape[1]}")


if __name__ == "__main__":
    main()
```

运行一次：

```powershell
.\.venv\Scripts\python.exe .\import_chroma.py
```

在当前快照下，预期数量为 3、维度为 512。会新建 chroma_db/，原 index/ 不变。数据由 Chroma 管理持久化，不手动编辑其 SQLite/索引内部文件。

这里有两个层级：collection 的 metadata 记录模型与构建方式；每条记录的 metadata 保存 source。embedding_function=None 加上显式 embeddings，使本实验始终使用你自己生成的向量，不触发另一个默认模型。

配置 cosine 是为了与原先的归一化点积对照。当前配置接口和距离公式见 [官方索引配置说明](https://docs.trychroma.com/docs/collections/configure)。显式传 documents 与 embeddings 时，Chroma 保存这两者，不重新向量化正文。[官方写入说明](https://docs.trychroma.com/docs/collections/add-data)

重复执行时若提示集合已存在，这是本教程的保护行为。若首次导入中断，也可能留下空或部分集合；先检查再决定。可以明确选择新名字重新导入：

```powershell
.\.venv\Scripts\python.exe .\import_chroma.py --collection rag_learning_v2
```

后续 inspect/search 也要使用同一个 --collection 名。第一轮正常成功则继续使用默认 v1；不要为了重试直接重置整个数据库。

本次写入一次处理 3 条记录即可；以后大量笔记需要批次写入与更新设计，不把这个演示当作生产全库导入器。

## 4. 按 ID 读取并检查字段

手动新建 inspect_chroma.py：

```python
import argparse
import json
from pathlib import Path

import chromadb


ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "chroma_db"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="rag_learning_v1")
    parser.add_argument("--id", default="lab_rules.txt#chunk-1")
    args = parser.parse_args()

    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(
        name=args.collection,
        embedding_function=None,
    )

    print(f"集合：{collection.name}，记录数量：{collection.count()}")
    print("集合配置元数据：")
    print(json.dumps(collection.metadata, ensure_ascii=False, indent=2))

    result = collection.get(
        ids=[args.id],
        include=["documents", "metadatas", "embeddings"],
    )

    if not result["ids"]:
        raise SystemExit("没有这个 ID；请核对 index/metadata.json。")

    print("\nID：", result["ids"][0])
    print("来源：", result["metadatas"][0]["source"])
    print("正文：", result["documents"][0])
    print("向量维度：", len(result["embeddings"][0]))


if __name__ == "__main__":
    main()
```

```powershell
.\.venv\Scripts\python.exe .\inspect_chroma.py
```

对照原 JSON，核对正文、来源和 ID；维度应与原矩阵一致。不需要把所有 512 个数字打印出来。

get 是按 ID/条件读取记录，没有进行语义相关度排序。query 才执行相似检索。[官方 get/query 区别](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 5. 编写数据库版检索

手动新建 search_chroma.py：

```python
import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "chroma_db"


def retrieve(question, top_k=2, source=None, collection_name="rag_learning_v1"):
    if top_k < 1:
        raise ValueError("top_k 必须大于等于 1。")
    if not question.strip():
        raise ValueError("问题不能为空。")

    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_collection(
        name=collection_name,
        embedding_function=None,
    )

    count = collection.count()
    if count == 0:
        return []

    config = collection.metadata
    if config.get("metric") != "cosine" or not config.get("normalized"):
        raise ValueError("集合不符合本教程的 cosine/归一化数据契约。")

    model = SentenceTransformer(config["model_name"], device="cpu")
    query_vector = model.encode(
        [config["query_prefix"] + question],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    response = collection.query(
        query_embeddings=query_vector.tolist(),
        n_results=min(top_k, count),
        where={"source": source} if source is not None else None,
        include=["documents", "metadatas", "distances"],
    )

    # query 支持批量问题。这里只有一个问题，先取第 0 组结果。
    hits = []
    for record_id, document, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        hits.append({
            "id": record_id,
            "text": document,
            "source": metadata["source"],
            "distance": float(distance),
            "score": 1.0 - float(distance),
        })

    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--source")
    parser.add_argument("--collection", default="rag_learning_v1")
    args = parser.parse_args()

    hits = retrieve(args.question, args.top_k, args.source, args.collection)
    if not hits:
        print("没有匹配记录；请检查集合数量和来源过滤条件。")

    for rank, item in enumerate(hits, start=1):
        print(f"\n[{rank}] {item['id']}")
        print(f"距离：{item['distance']:.4f}，相似度：{item['score']:.4f}")
        print(item["text"])


if __name__ == "__main__":
    main()
```

```powershell
.\.venv\Scripts\python.exe .\search_chroma.py "预约实验室需要提前多久？"
.\.venv\Scripts\python.exe .\search_chroma.py "设备坏了，需要提供什么信息？"
.\.venv\Scripts\python.exe .\search_chroma.py "访客能访问内部测试设备吗？"
```

query_embeddings 显式传入你生成的问题向量；include 指定需要返回的字段。ids 总会返回，不需要加入 include。单个问题的返回值也是二维分组，所以读取 response["ids"][0]，不同于 get 的一维 ID 列表。[官方查询接口](https://docs.trychroma.com/docs/querying-collections/query-and-get)

本例每次命令都重新启动 Python 和加载模型；这适合学习，不能据此判断数据库本身的查询性能。

## 6. 验证来源过滤

```powershell
.\.venv\Scripts\python.exe .\search_chroma.py "需要提前多久预约？" --source lab_rules.txt

.\.venv\Scripts\python.exe .\search_chroma.py "需要提前多久预约？" --source network.txt

.\.venv\Scripts\python.exe .\search_chroma.py "需要提前多久预约？" --source nonexistent.txt
```

第一条只能返回 lab_rules.txt。第二条只能返回网络资料：它可能与预约无关，但仍会作为指定范围内的候选返回。第三条应无匹配记录。

where 是依据 metadata 的过滤，不是全文关键词搜索，也不是相关性判断。source 的值是索引中保存的相对路径，必须匹配，例如后面可能变成 project_notes/LEARNING_NOTES.md。

## 7. 与 NumPy 基线对照

对同一问题分别运行：

```powershell
.\.venv\Scripts\python.exe .\search.py "设备坏了，需要提供什么信息？" --top-k 2
.\.venv\Scripts\python.exe .\search_chroma.py "设备坏了，需要提供什么信息？" --top-k 2
```

记录 ID、来源、正文、顺序和分数。对当前小语料，预期能找到同一份设备说明；不要事先编造实际分数。

Chroma cosine 返回 distance，越小越近；原 NumPy 返回 similarity，越大越近。转换 score = 1 - distance 后才能按相同语义比较。浮点误差允许小偏差，近似检索和并列结果也可能影响顺序。

如果明显不一致，先检查集合名、向量快照、模型、查询前缀、归一化和距离度量；不要直接更换回答模型。

## 8. 验证持久化

关闭正在用的终端，重新打开 PowerShell：

```powershell
cd C:\ttchina\06_Gitlab\08_RAGLearn
.\.venv\Scripts\python.exe .\inspect_chroma.py
.\.venv\Scripts\python.exe .\search_chroma.py "实验室几点开放？"
```

不重跑 import、不重新写入数据。仍能读取相同数量、ID 和原文，才说明验证了持久化读取。脚本用自身所在位置定位 chroma_db/，避免启动目录变化导致误建另一个数据库。

## 9. 独立练习增删改查

手动新建 crud_chroma.py。这里只操作独立 rag_learning_crud 集合中的两个 lesson-demo ID，不改变主集合。代码中的开放时间是虚构练习数据，不能解释成原实验室规定。

```python
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent


def main():
    client = chromadb.PersistentClient(path=str(ROOT / "chroma_db"))
    base = client.get_collection("rag_learning_v1", embedding_function=None)
    config = base.metadata
    before = base.count()

    lab = client.get_or_create_collection(
        name="rag_learning_crud",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"model_name": config["model_name"]},
    )
    if lab.metadata.get("model_name") != config["model_name"]:
        raise SystemExit("练习集合模型不同，请明确使用新的练习集合名。")
    if lab.count() != 0:
        raise SystemExit("练习集合非空，请先检查上一次是否中断；本脚本不自动清空。")

    model = SentenceTransformer(config["model_name"], device="cpu")

    def vectorize(text):
        return model.encode([text], normalize_embeddings=True).tolist()

    record_id = "lesson-demo-001"
    original = "数据库练习：图书角每天十点开放。"
    changed = "数据库练习：图书角每天十一点开放。"

    lab.add(
        ids=[record_id],
        documents=[original],
        embeddings=vectorize(original),
        metadatas=[{"source": "crud_demo", "revision": 1}],
    )
    print("add 后数量：", lab.count())
    print("get：", lab.get(ids=[record_id], include=["documents", "metadatas"]))

    # 正文发生变化，必须同步更新它的向量。
    lab.update(
        ids=[record_id],
        documents=[changed],
        embeddings=vectorize(changed),
        metadatas=[{"source": "crud_demo", "revision": 2}],
    )
    print("update：", lab.get(ids=[record_id], include=["documents", "metadatas"]))

    # upsert 对已有 ID 更新、对不存在的 ID 新增。
    other = "数据库练习：图书角提供工具书借阅。"
    lab.upsert(
        ids=[record_id, "lesson-demo-002"],
        documents=[changed, other],
        embeddings=model.encode([changed, other], normalize_embeddings=True).tolist(),
        metadatas=[{"source": "crud_demo"}, {"source": "crud_demo"}],
    )
    print("upsert 后数量：", lab.count())

    lab.delete(ids=[record_id, "lesson-demo-002"])
    print("delete 后数量：", lab.count())
    print("删除后按 ID 读取：", lab.get(ids=[record_id]))

    if lab.count() != 0 or base.count() != before:
        raise SystemExit("数量检查不通过，请检查数据库状态。")
    print("主集合数量保持不变：", base.count())


if __name__ == "__main__":
    main()
```

```powershell
.\.venv\Scripts\python.exe .\crud_chroma.py
.\.venv\Scripts\python.exe .\inspect_chroma.py
```

预期练习集合数量依次为 1、1、2、0；update 后原文变为十一点，主集合仍是 3 条。删除后 get 的 ids 应为空。最终保留空的练习集合，便于重复执行。

如果你第一轮使用的是 v2，先把 crud_chroma.py 中读取 base 的集合名改成对应名称。

get_or_create_collection 遇到已有集合不会按新参数自动重建其配置；本例只把它用于可重复的独立 CRUD 练习，并检查残留与模型。主导入仍使用 create_collection。

upsert 的语义见 [官方更新说明](https://docs.trychroma.com/docs/collections/update-data)，按 ID 删除见 [官方删除说明](https://docs.trychroma.com/docs/collections/delete-data)。不要用 client.reset() 代替本练习的精确删除。

## 10. 接回现有 Codex 回答阶段

先检查当前 CLI 状态，由你执行：

```powershell
codex --version
codex login status
```

在编辑器中手动新建 ask_chroma.py，复制现有 ask.py 的内容，只替换一行：

```python
# 原来：
from search import retrieve

# 数据库版使用：
from search_chroma import retrieve
```

保留实际导入行即可，不把两行同时留下。新的 retrieve 仍返回 id/source/text/score，所以原有提示词、引用编号、Codex CLI 调用方式都可以沿用。若使用 v2，在 ask_chroma.py 中获取 hits 的那一行明确传入集合名：

```python
hits = retrieve(args.question, args.top_k, collection_name="rag_learning_v2")
```

默认 v1 不需要这处改动。第一轮接回回答时先不带来源过滤，以便与原版同输入对照。

```powershell
.\.venv\Scripts\python.exe .\ask_chroma.py "预约实验室需要提前多久？"
.\.venv\Scripts\python.exe .\ask_chroma.py "实验室几点开放，设备坏了需要报告什么？"
.\.venv\Scripts\python.exe .\ask_chroma.py "管理员的手机号码是多少？"
```

先看打印出的参考片段，再检查回答与引用。最后一问资料中没有答案，应明确说明现有资料无法回答。CLI 返回成功和出现引用编号都不足以证明答案正确。

沿用的 ask.py 是项目已有的 stdin → codex exec → 最终回答文件模式。它需要联网，问题和参考片段会发送给 Codex；“只依据资料、不调用工具”仍是提示词要求。官方运行模式可参考 [Codex 非交互说明](https://learn.chatgpt.com/docs/non-interactive-mode)。

## 11. 第一轮验收表

把实际结果简短记录到 HANDOFF.md，或把输出交给助手在你授权下整理。以下项目都需要你运行后填写，不能预填为通过。

| 检查 | 通过标准 |
| --- | --- |
| NumPy 基线 | 原版仍能读取索引并检索 |
| 导入 | 主集合 3 条，模型信息和 512 维对应 |
| 按 ID 读取 | 原文、source、ID 与快照一致 |
| 相似检索 | 固定问题返回包含答案的片段 |
| 来源过滤 | 结果 source 全部满足指定条件；不存在来源返回空 |
| 数值对照 | 明确 cosine 距离方向；和基线对照 ID、原文、分数 |
| 持久化 | 关闭进程重开后可读，无须再次导入 |
| CRUD | 演示集合数量 1 → 1 → 2 → 0，主集合不变 |
| 回答 | 回答事实正确；引用支持对应结论 |
| 语料外问题 | 不编造管理员手机号等资料外信息 |

运行成功后可由你保存实际依赖版本：

```powershell
.\.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 requirements-chroma.txt
```

这份文件记录当前环境，不能代替可重建环境的实际验证。

## 12. 再尝试本项目自己的 Markdown 文档

先完成第一轮三条示例的对照，再进行这一阶段。当前 build_index.py 的后缀集合存在一个点号遗漏，由你先修改：

```python
# 当前：{'.txt', 'md'}
# 应为：{'.txt', '.md'}
```

先只选本项目一份文档，比如 docs/LEARNING_NOTES.md。由你复制到明确的输入子目录：

```powershell
New-Item -ItemType Directory -Force -Path .\data\project_notes
Copy-Item -LiteralPath .\docs\LEARNING_NOTES.md -Destination .\data\project_notes\LEARNING_NOTES.md
```

只在目标副本尚未存在时首次复制；若已存在，先自行核对，不覆盖未知内容。索引的是这个副本，不会自动跟踪 docs/ 原文的后续修改。

这次重跑会更新 index/ 中的 NumPy 快照；若要保留第一轮旧快照，先自行备份。旧 Chroma v1 仍保留原数据。

```powershell
.\.venv\Scripts\python.exe .\build_index.py
.\.venv\Scripts\python.exe .\import_chroma.py --collection rag_project_notes_v1
.\.venv\Scripts\python.exe .\search_chroma.py "embeddings.npy 是向量数据库吗？" --collection rag_project_notes_v1 --source project_notes/LEARNING_NOTES.md
```

检查 Markdown 的片段是否真的出现，不能只看程序成功退出。如果长度检查报错，先查看对应 chunk，并减小切块大小；不能忽略模型输入长度限制。

字符切块可能把标题、表格或代码块拆开，先记录具体反例，再学习按 Markdown 结构切块。本阶段暂不解析 wikilink 或读取其目标，不把文档中出现的文件路径当作访问授权。

若要让 ask_chroma.py 回答这批文档，把获取 hits 的集合名改为 rag_project_notes_v1，再运行并核对引用。collection 中已有数据不会因 data/ 或 docs/ 文档变化自动更新；原文变更后需重新构建快照并采用明确的集合更新策略。

## 13. 错误排查

| 现象 | 优先检查 |
| --- | --- |
| ModuleNotFoundError: chromadb | 安装与运行是否使用同一个 .venv |
| configuration 参数不支持 | 查看 Chroma 实际版本与对应官方接口，不混用旧配置示例 |
| collection 已存在 | 导入故意停止；先查看内容，再指定新集合名 |
| collection 不存在 | 数据库路径、名称、导入是否成功 |
| 查询维度不匹配 | 模型与已有集合的向量空间是否一致，不能仅凭维度相同就混用 |
| 默认模型下载或要求 API Key | 是否忘了 embedding_function=None 或显式 embeddings/query_embeddings |
| 过滤没有结果 | source 是否与存入的相对路径一致 |
| 数量不再是 3 | 是否增加了语料、选错集合或上次导入中断 |
| 改正文后仍检索旧结果 | 是否同步更新向量、使用了新快照对应的集合 |
| CRUD 提示练习集合非空 | 上次可能中断；先按 ID 检查，不清空整个数据库 |
| NumPy 正确但数据库排序不同 | 核对快照、模型、前缀、归一化、度量与近似检索因素 |
| 检索正确但回答错误 | 检查实际参考片段、提示词、引用与生成结果 |
| Codex 调用失败 | 分开检查 CLI 登录、实际错误、用量与连接；数据库成功不证明生成成功 |

后续个人 Obsidian 接入需要明确选取范围、排除规则、来源定位和是否允许向云端发送片段。本教程不授权扫描或导入个人 Vault，也不包含自动写回笔记。

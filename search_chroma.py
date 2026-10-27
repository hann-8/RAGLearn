import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "chroma_db"

def retrieve(question, top_k=2, source=None, collection_name="rag_learning_v1"):
    if top_k < 1:
        raise ValueError("top_k必须大于等于1。")
    if not question.strip():
        raise ValueError("问题不能为空。")

    #创建一个持久化数据库对象，一个Chroma客户端，path是数据库路径，可以持久性读写进磁盘（否则将写入内存）
    client = chromadb.PersistentClient(path=str(DB_DIR))
    #获取已有的集合，类似关系库中的“表”
    collection = client.get_collection(
        name = collection_name,
        embedding_function=None,
    )

    count = collection.count()
    if count == 0:
        return []

    config = collection.metadata
    if config.get("metric") != "cosine" or not config.get("normalized"):
        raise ValueError("集合不符合本教程的 cosine/归一化数据契约")

    #创建和向量化知识库用到的一样的模型，复用 metadata["model_name"]
    model = SentenceTransformer(config["model_name"], device="cpu")
    #encode metadata["query_prefix"]+question
    query_vector = model.encode(
        [config["query_prefix"] + question],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    #进行查询动作，传入的是将Numpy递归地转成python嵌套list结构的query_vector
    response = collection.query(
        query_embeddings=query_vector.tolist(),
        n_results=min(top_k, count),
        where={"source":source} if source is not None else None,
        include=["documents", "metadatas", "distances"],
    )

    #query 支持批量问题，这里只有一个问题，先取第0组结果
    hits = []
    for record_id, document, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        hits.append({
            "id":record_id,
            "text":document,
            "source":metadata["source"],
            "distance":float(distance),
            "score":1.0-float(distance),
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
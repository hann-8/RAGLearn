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
    #默认创建一个叫rag_learning_v1的collection对象，学习用
    parser.add_argument("--collection", default="rag_learning_v1")
    args = parser.parse_args()

    snapshot = json.loads(
        (INDEX_DIR / "metadata.json").read_text(encoding="utf-8")
    )
    vectors = np.load(INDEX_DIR / "embeddings.npy", allow_pickle=False)
    chunks = snapshot["chunks"]
    ids = [chunk["id"] for chunk in chunks]

    if not chunks:
        raise SystemExit("快照没有chunk，检查index/。")
    if vectors.ndim !=2 or vectors.shape[0] != len(chunks):
        raise SystemExit("chunk 数量和向量矩阵不对应，停止导入。")
    if len(set(ids)) != len(ids):
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
        raise SystemExit("导入后数量不符，请检查数据库内容")

    print(f"数据库目录：{DB_DIR}")
    print(f"集合：{collection.name}")
    print(f"记录数量：{collection.count()}")
    print(f"向量维度：{vectors.shape[1]}")

if __name__ == '__main__':
    main()
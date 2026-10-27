import argparse
import json
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "chroma_db"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="rag_learning_v1")
    parser.add_argument("--id", default="network.txt#chunk-1")
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
        include=["documents", "metadatas","embeddings"],
    )

    if not result["ids"]:
        raise SystemExit("没有这个ID，请核对 index/metadata.json。")

    print("\nID: ", result["ids"][0])
    print("来源: ", result["metadatas"][0]["source"])
    print("正文: ", result["documents"][0])
    print("向量维度: ", len(result["embeddings"][0]))

if __name__ == '__main__':
    main()
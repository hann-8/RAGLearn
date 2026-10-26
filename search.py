import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
INDEX_DIR = ROOT / 'index'

def retrieve(question, top_k=2):
    if top_k <1:
        raise ValueError('top_k必须大于等于1.')

    metadata = json.loads(
        (INDEX_DIR / 'metadata.json').read_text(encoding='utf-8')
    )

    embeddings = np.load(
        INDEX_DIR / 'embeddings.npy',
        allow_pickle=False,
    )

    chunks = metadata['chunks']

    if embeddings.shape[0] != len(chunks):
        raise ValueError('文本与向量不一致，请重新建立索引。')

    model = SentenceTransformer(
        metadata['model_name'],
        device='cpu'
    )

    query_vector = model.encode(
        metadata['query_prefix'] + question,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    scores = embeddings @ query_vector
    positions = np.argsort(-scores)[:top_k]

    results = []

    for position in positions:
        item = dict(chunks[int(position)])
        item['score'] = float(scores[position])
        results.append(item)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--top-k', type=int, default=2)
    args = parser.parse_args()

    results = retrieve(args.question, args.top_k)

    for rank, item in enumerate(results, start=1):
        print(f"\n[{rank}]{item['id']}")
        print(f"相似度:{item['score']:.4f}")
        print(item['text'])


if __name__ == '__main__':
    main()
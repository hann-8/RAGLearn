import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
INDEX_DIR = ROOT / 'index'

MODEL_NAME = 'BAAI/bge-small-zh-v1.5'
QUERY_PREFIX = '为这个句子生成表示以用于检索相关文章：'

CHUNK_SIZE = 300
CHUNK_OVERLAP = 60

def split_text(text):
    '''按字符切块，相邻块保留部分重叠内容'''
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start+CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks

def main():
    chunks = []
    for path in sorted(DATA_DIR.rglob('*')):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {'.txt','md'}:
            continue
        text = path.read_text(encoding='utf-8-sig')
        source = path.relative_to(DATA_DIR).as_posix()

        for number, content in enumerate(split_text(text), start = 1):
            chunks.append(
                {
                    'id':f'{source}#chunk-{number}',
                    'source':source,
                    'text':content,
                }
            )

    if not chunks:
        raise SystemExit('data目录中无可索引的文本')

    model = SentenceTransformer(MODEL_NAME, device='cpu')
    texts = [chunk['text'] for chunk in chunks]

    #防止以后换资料时，过长文本被模型静默截断
    for chunk in chunks:
        token_ids = model.tokenizer(
            chunk['text'],
            truncation=False,
        )['input_ids']

        if len(token_ids) > model.max_seq_length:
            raise ValueError(
                f"{chunk['id']}超过模型长度限制，请减小切块大小"
            )

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    metadata = {
        'model_name':MODEL_NAME,
        'query_prefix':QUERY_PREFIX,
        'chunk_size':CHUNK_SIZE,
        'chunk_overlap':CHUNK_OVERLAP,
        'chunks':chunks,
    }

    INDEX_DIR.mkdir(exist_ok=True)

    np.save(
        INDEX_DIR / 'embeddings.npy',
        embeddings.astype(np.float32),
    )

    (INDEX_DIR / 'metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    print(f'片段数量:{len(chunks)}')
    print(f'向量矩阵形状:{embeddings.shape}')
    print(f'索引目录:{INDEX_DIR}')

if __name__ == '__main__':
    main()
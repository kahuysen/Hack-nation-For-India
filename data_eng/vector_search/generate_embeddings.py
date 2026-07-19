"""Generate normalized BGE embeddings locally and write a Parquet artifact."""

import argparse
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .config import settings
from .contracts import DOCUMENT_COLUMNS, EMBEDDING_COLUMN, require_columns, validate_unique_ids


def generate_embeddings(
    input_path: Path,
    output_path: Path,
    model_name: str = settings.model_name,
    expected_dimension: int = settings.embedding_dimension,
    batch_size: int = 64,
) -> int:
    from fastembed import TextEmbedding

    documents = pq.read_table(input_path)
    require_columns(documents.column_names, DOCUMENT_COLUMNS, "document Parquet")
    validate_unique_ids(documents.column("document_id").to_pylist())
    texts = documents.column("document_text").to_pylist()
    model = TextEmbedding(model_name=model_name)
    vectors = []
    for completed, vector in enumerate(
        model.embed(texts, batch_size=batch_size), start=1
    ):
        vectors.append(np.asarray(vector, dtype=np.float32))
        if completed % 500 == 0 or completed == len(texts):
            print(f"Embedded {completed}/{len(texts)} documents", flush=True)
    if len(vectors) != len(texts):
        raise RuntimeError("Embedding model returned a different number of vectors")
    dimensions = {vector.shape[0] for vector in vectors}
    if dimensions != {expected_dimension}:
        raise ValueError(
            f"Expected {expected_dimension}-dimensional embeddings, got {sorted(dimensions)}"
        )
    embedding_array = pa.array(
        [vector.tolist() for vector in vectors], type=pa.list_(pa.float32())
    )
    output = documents.append_column(EMBEDDING_COLUMN, embedding_array)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(f"{output_path.suffix}.partial")
    pq.write_table(output, partial_path, compression="zstd")
    partial_path.replace(output_path)
    return output.num_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=settings.documents_path)
    parser.add_argument("--output", type=Path, default=settings.embeddings_path)
    parser.add_argument("--model", default=settings.model_name)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    count = generate_embeddings(args.input, args.output, args.model, batch_size=args.batch_size)
    print(f"Wrote {count} embeddings to {args.output}")


if __name__ == "__main__":
    main()

import argparse
import logging
from pathlib import Path

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.rag.ingestion import create_document_chunks, ingest_directory, load_documents


logger = logging.getLogger(__name__)
DEFAULT_KNOWLEDGE_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest enterprise support documents.")
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_KNOWLEDGE_DIRECTORY,
        help="Directory containing Markdown or text knowledge documents.",
    )
    parser.add_argument("--chunk-size", type=int, default=1_000)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and chunk documents without writing to the database.",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()

    if args.dry_run:
        documents = load_documents(args.directory)
        chunks = create_document_chunks(
            documents,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        logger.info("Dry run loaded %d documents into %d chunks", len(documents), len(chunks))
        return 0

    with SessionLocal() as db:
        chunk_count = ingest_directory(
            db,
            args.directory,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
    logger.info("Ingested %d knowledge chunks", chunk_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
ChromaDB Persistent Vector Store Service
FR-010 to FR-014: Vector database for financial documents and market intelligence.
Uses chromadb.PersistentClient with sentence-transformers/all-MiniLM-L6-v2 embeddings.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chroma_service")

# ChromaDB persistent data directory (relative to project root)
CHROMA_DB_PATH = str(Path(__file__).resolve().parents[5] / "data" / "chroma_db")

_chroma_client = None
_financial_docs_collection = None
_market_intel_collection = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            logger.info(f"ChromaDB PersistentClient initialized at: {CHROMA_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    return _chroma_client


def _get_financial_docs_collection():
    global _financial_docs_collection
    if _financial_docs_collection is None:
        client = _get_client()
        try:
            from chromadb.utils import embedding_functions
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            _financial_docs_collection = client.get_or_create_collection(
                name="financial_documents",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'financial_documents' ready.")
        except Exception as e:
            logger.error(f"Failed to get/create 'financial_documents' collection: {e}")
            raise
    return _financial_docs_collection


def _get_market_intel_collection():
    global _market_intel_collection
    if _market_intel_collection is None:
        client = _get_client()
        try:
            from chromadb.utils import embedding_functions
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            _market_intel_collection = client.get_or_create_collection(
                name="market_intelligence",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection 'market_intelligence' ready.")
        except Exception as e:
            logger.error(f"Failed to get/create 'market_intelligence' collection: {e}")
            raise
    return _market_intel_collection


class ChromaService:
    """
    Persistent ChromaDB vector store service.
    Collections:
      - financial_documents: Document chunks from uploaded financial docs
      - market_intelligence: External market events and economic indicators
    """

    @staticmethod
    def add_document_chunks(
        ticker: str,
        doc_id: str,
        chunks: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add or upsert document text chunks into the 'financial_documents' collection.

        Args:
            ticker: Company ticker symbol (e.g. "AAPL")
            doc_id: Unique document identifier (used as ID prefix)
            chunks: List of text chunk strings
            metadatas: List of metadata dicts corresponding to each chunk

        Returns:
            Dict with status and count of chunks added
        """
        if not chunks:
            return {"status": "SKIPPED", "chunks_added": 0, "reason": "No chunks provided"}

        try:
            collection = _get_financial_docs_collection()

            # Build unique IDs: doc_id__chunk_<index>
            ids = [f"{doc_id}__chunk_{i}" for i in range(len(chunks))]

            # Ensure each metadata entry has at minimum ticker and doc_id
            safe_metadatas = []
            for i, meta in enumerate(metadatas):
                m = dict(meta)
                m["ticker"] = ticker.upper()
                m["doc_id"] = str(doc_id)
                # ChromaDB metadata values must be str/int/float/bool — convert complex types
                sanitized = {}
                for k, v in m.items():
                    if isinstance(v, (str, int, float, bool)):
                        sanitized[k] = v
                    else:
                        sanitized[k] = str(v)
                safe_metadatas.append(sanitized)

            collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=safe_metadatas
            )

            logger.info(f"Upserted {len(chunks)} chunks for doc '{doc_id}' (ticker={ticker}) into ChromaDB.")
            return {
                "status": "INDEXED",
                "ticker": ticker.upper(),
                "doc_id": str(doc_id),
                "chunks_added": len(chunks)
            }
        except Exception as e:
            logger.error(f"ChromaDB add_document_chunks failed for doc '{doc_id}': {e}")
            return {"status": "FAILED", "error": str(e), "chunks_added": 0}

    @staticmethod
    def search_similar(
        query: str,
        ticker: Optional[str] = None,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Cosine similarity search over the 'financial_documents' collection.

        Args:
            query: Natural language search query
            ticker: Optional company ticker to filter results
            n_results: Number of top results to return

        Returns:
            Dict with 'results' list of matching chunks with metadata and distances
        """
        try:
            collection = _get_financial_docs_collection()

            where_filter = None
            if ticker and ticker.upper() != "ALL":
                where_filter = {"ticker": ticker.upper()}

            query_kwargs: Dict[str, Any] = {
                "query_texts": [query],
                "n_results": min(n_results, max(1, collection.count()))
            }
            if where_filter:
                query_kwargs["where"] = where_filter

            if collection.count() == 0:
                return {"query": query, "results": [], "total_found": 0}

            response = collection.query(**query_kwargs)

            results = []
            docs = response.get("documents", [[]])[0]
            metas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]
            ids = response.get("ids", [[]])[0]

            for i, (doc_text, meta, dist, rid) in enumerate(zip(docs, metas, distances, ids)):
                # ChromaDB cosine distance: similarity = 1 - distance
                similarity = round(1.0 - float(dist), 4)
                results.append({
                    "id": rid,
                    "text": doc_text,
                    "metadata": meta,
                    "similarity_score": similarity,
                    "rank": i + 1
                })

            return {
                "query": query,
                "ticker_filter": ticker.upper() if ticker else None,
                "results": results,
                "total_found": len(results)
            }
        except Exception as e:
            logger.error(f"ChromaDB search_similar failed: {e}")
            return {"query": query, "results": [], "total_found": 0, "error": str(e)}

    @staticmethod
    def add_market_event(
        event_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add or upsert a market intelligence event into the 'market_intelligence' collection.

        Args:
            event_id: Unique event identifier
            text: Event text content (title + summary)
            metadata: Event metadata dict

        Returns:
            Dict with status
        """
        try:
            collection = _get_market_intel_collection()

            safe_meta: Dict[str, Any] = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v
                else:
                    safe_meta[k] = str(v)

            collection.upsert(
                ids=[str(event_id)],
                documents=[text],
                metadatas=[safe_meta]
            )

            logger.info(f"Upserted market event '{event_id}' into ChromaDB.")
            return {"status": "INDEXED", "event_id": str(event_id)}
        except Exception as e:
            logger.error(f"ChromaDB add_market_event failed for event '{event_id}': {e}")
            return {"status": "FAILED", "error": str(e)}

    @staticmethod
    def get_collection_stats() -> Dict[str, Any]:
        """
        Returns document counts for both ChromaDB collections.

        Returns:
            Dict with counts for 'financial_documents' and 'market_intelligence'
        """
        stats: Dict[str, Any] = {
            "chroma_db_path": CHROMA_DB_PATH,
            "financial_documents_count": 0,
            "market_intelligence_count": 0,
            "status": "READY"
        }
        try:
            fin_col = _get_financial_docs_collection()
            stats["financial_documents_count"] = fin_col.count()
        except Exception as e:
            stats["financial_documents_error"] = str(e)
            stats["status"] = "PARTIAL"

        try:
            mi_col = _get_market_intel_collection()
            stats["market_intelligence_count"] = mi_col.count()
        except Exception as e:
            stats["market_intelligence_error"] = str(e)
            stats["status"] = "PARTIAL"

        return stats

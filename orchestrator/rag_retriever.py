import os
import logging
from typing import List, Optional, Dict, Any
import pinecone
import openai

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RelevantDoc:
    def __init__(self, id: str, score: float, metadata: Dict[str, Any], content: str):
        self.id = id
        self.score = score
        self.metadata = metadata
        self.content = content

class ContextRetriever:
    """
    ContextRetriever uses Pinecone vector database and OpenAI embeddings
    to index documents and query relevant context.
    """

    DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
    MODEL_DIMENSIONS = {
        "text-embedding-ada-002": 1536
    }

    def __init__(
        self,
        pinecone_api_key: Optional[str] = None,
        pinecone_env: Optional[str] = None,
        index_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        namespace: Optional[str] = None
    ):
        self.pinecone_api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
        self.pinecone_env = pinecone_env or os.getenv("PINECONE_ENVIRONMENT")
        if not self.pinecone_api_key or not self.pinecone_env:
            raise ValueError("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set")
        pinecone.init(api_key=self.pinecone_api_key, environment=self.pinecone_env)

        self.index_name = index_name or os.getenv("PINECONE_INDEX", "analysis-context")
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL", self.DEFAULT_EMBEDDING_MODEL)
        if self.embedding_model not in self.MODEL_DIMENSIONS:
            raise ValueError(f"Unknown embedding model {self.embedding_model}")
        self.dimension = self.MODEL_DIMENSIONS[self.embedding_model]
        self.namespace = namespace or os.getenv("PINECONE_NAMESPACE")

        if self.index_name not in pinecone.list_indexes():
            logger.info(f"Creating Pinecone index `{self.index_name}` with dimension {self.dimension}")
            pinecone.create_index(self.index_name, dimension=self.dimension, metric="cosine")
        self.index = pinecone.Index(self.index_name)

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        openai.api_key = openai_api_key

    def _embed(self, texts: List[str]) -> List[List[float]]:
        try:
            response = openai.Embedding.create(model=self.embedding_model, input=texts)
            return [datum["embedding"] for datum in response["data"]]
        except Exception as e:
            logger.exception("Failed to generate embeddings")
            raise

    def index_documents(self, docs: List[str], ids: Optional[List[str]] = None, metadatas: Optional[List[Dict[str, Any]]] = None, batch_size: int = 100):
        """
        Generates embeddings for the provided docs and upserts them into Pinecone.
        docs: list of document strings to index.
        ids: optional list of unique IDs for each document. If None, uses incremental IDs.
        metadatas: optional list of metadata dicts.
        """
        if not docs:
            logger.warning("No documents provided to index.")
            return
        total = len(docs)
        ids = ids or [str(i) for i in range(total)]
        metadatas = metadatas or [{} for _ in range(total)]
        for i in range(0, total, batch_size):
            batch_docs = docs[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            try:
                embeddings = self._embed(batch_docs)
                to_upsert = list(zip(batch_ids, embeddings, batch_meta))
                self.index.upsert(vectors=to_upsert, namespace=self.namespace)
                logger.info(f"Upserted batch {i//batch_size + 1}: {len(to_upsert)} vectors")
            except Exception:
                logger.exception(f"Failed to upsert batch starting at index {i}")
                raise

    def query(self, query_text: str, top_k: int = 5) -> List[RelevantDoc]:
        """
        Queries the Pinecone index for the most relevant documents to the query_text.
        Returns a list of RelevantDoc instances.
        """
        try:
            embedding = self._embed([query_text])[0]
            query_response = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace
            )
            matches = query_response.get("matches", [])
            results: List[RelevantDoc] = []
            for m in matches:
                doc = RelevantDoc(
                    id=m.get("id"),
                    score=m.get("score", 0.0),
                    metadata=m.get("metadata", {}),
                    content=m.get("metadata", {}).get("text", "")
                )
                results.append(doc)
            return results
        except Exception:
            logger.exception("Failed to query Pinecone index")
            return []
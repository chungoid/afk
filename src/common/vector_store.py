import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.base import VectorStore
from langchain.vectorstores import Pinecone, Weaviate, FAISS
import pinecone
import weaviate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreError(Exception):
    """Custom exception for VectorStoreClient errors."""
    pass

class VectorStoreClient:
    """
    A client for interacting with various vector store backends (Pinecone, Weaviate, FAISS).
    Environment variables:
        VECTOR_STORE_TYPE: 'pinecone' | 'weaviate' | 'faiss'
        PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX
        WEAVIATE_URL, WEAVIATE_INDEX
        FAISS_INDEX_PATH
    """
    def __init__(self):
        self.store_type = os.getenv("VECTOR_STORE_TYPE", "faiss").lower()
        self.embeddings = OpenAIEmbeddings()
        self.client: VectorStore
        try:
            if self.store_type == "pinecone":
                self._init_pinecone()
            elif self.store_type == "weaviate":
                self._init_weaviate()
            elif self.store_type == "faiss":
                self._init_faiss()
            else:
                raise VectorStoreError(f"Unsupported VECTOR_STORE_TYPE: {self.store_type}")
            logger.info(f"Vector store initialized: {self.store_type}")
        except Exception as e:
            logger.exception("Failed to initialize vector store")
            raise

    def _init_pinecone(self):
        api_key = os.getenv("PINECONE_API_KEY")
        env = os.getenv("PINECONE_ENVIRONMENT")
        index_name = os.getenv("PINECONE_INDEX")
        if not api_key or not env or not index_name:
            raise VectorStoreError("Pinecone settings PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX required")
        pinecone.init(api_key=api_key, environment=env)
        index = pinecone.Index(index_name)
        self.client = Pinecone.from_existing_index(index=index, embedding=self.embeddings)

    def _init_weaviate(self):
        url = os.getenv("WEAVIATE_URL")
        index_name = os.getenv("WEAVIATE_INDEX")
        if not url or not index_name:
            raise VectorStoreError("Weaviate settings WEAVIATE_URL, WEAVIATE_INDEX required")
        client = weaviate.Client(url=url)
        self.client = Weaviate(client=client, index_name=index_name, embedding=self.embeddings)

    def _init_faiss(self):
        index_path = os.getenv("FAISS_INDEX_PATH", "faiss_index")
        if os.path.isdir(index_path):
            self.client = FAISS.load_local(folder_path=index_path, embeddings=self.embeddings)
        else:
            # initialize empty index
            self.client = FAISS.from_texts(texts=[], embedding=self.embeddings)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> List[str]:
        """
        Add texts and optional metadata to the vector store.
        Returns list of ids under which embeddings were added.
        """
        if not texts:
            raise VectorStoreError("No texts provided to add_texts")
        n = len(texts)
        if ids and len(ids) != n:
            raise VectorStoreError("Length of ids must match number of texts")
        if metadatas and len(metadatas) != n:
            raise VectorStoreError("Length of metadatas must match number of texts")
        ids = ids or [str(uuid.uuid4()) for _ in range(n)]
        try:
            self.client.add_texts(texts=texts, metadatas=metadatas or [{}]*n, ids=ids)
            logger.info("Added %d embeddings to %s store", n, self.store_type)
            return ids
        except Exception as e:
            logger.exception("Error adding texts to vector store")
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform similarity search for a query string.
        Returns a list of dicts with keys: 'text', 'score', 'id', 'metadata'.
        """
        if not query:
            raise VectorStoreError("Empty query for similarity_search")
        try:
            results = self.client.similarity_search_with_score(query=query, k=k, **kwargs)
            structured = []
            for doc, score in results:
                structured.append({
                    "text": doc.page_content,
                    "score": score,
                    "id": getattr(doc, "id", None),
                    "metadata": doc.metadata
                })
            logger.info("Retrieved %d results for query from %s store", len(structured), self.store_type)
            return structured
        except Exception as e:
            logger.exception("Error during similarity search")
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def delete(self, ids: Optional[List[str]] = None, delete_all: bool = False) -> None:
        """
        Delete entries by ids or clear entire index.
        """
        try:
            if delete_all:
                if hasattr(self.client, "delete_all"):
                    self.client.delete_all()
                else:
                    raise VectorStoreError(f"delete_all not supported for {self.store_type}")
                logger.info("Deleted all entries from %s store", self.store_type)
            elif ids:
                self.client.delete(ids=ids)
                logger.info("Deleted %d entries from %s store", len(ids), self.store_type)
            else:
                raise VectorStoreError("Either ids or delete_all=True must be provided")
        except Exception as e:
            logger.exception("Error deleting entries from vector store")
            raise
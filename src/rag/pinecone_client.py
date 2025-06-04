import os
import logging
from typing import List, Dict, Any
import pinecone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PineconeClientError(Exception):
    pass

class PineconeClient:
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT")
        index_name = os.getenv("PINECONE_INDEX")

        if not api_key or not environment or not index_name:
            raise PineconeClientError("PINECONE_API_KEY, PINECONE_ENVIRONMENT, and PINECONE_INDEX must be set")

        try:
            pinecone.init(api_key=api_key, environment=environment)
            self.index = pinecone.Index(index_name)
            logger.info(f"Connected to Pinecone index '{index_name}' in environment '{environment}'")
        except Exception as e:
            logger.exception("Failed to initialize Pinecone client")
            raise PineconeClientError(str(e))

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def fetch_context(self, namespace: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-k context vectors and their metadata for a given namespace (e.g. conversation hash).
        Returns a list of dicts with keys: id, score, metadata.
        """
        try:
            logger.debug(f"Querying Pinecone namespace '{namespace}' for top_k={top_k}")
            result = self.index.query(
                namespace=namespace,
                top_k=top_k,
                include_metadata=True,
                include_values=False
            )
            matches = result.get("matches", [])
            context = [{"id": m["id"], "score": m["score"], "metadata": m.get("metadata", {})} for m in matches]
            logger.info(f"Retrieved {len(context)} context items from Pinecone")
            return context
        except Exception as e:
            logger.exception("Error querying Pinecone")
            raise

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def upsert_snippets(self, namespace: str, vectors: List[Dict[str, Any]]) -> None:
        """
        Upsert a batch of vectors into Pinecone under the given namespace.
        Each vector dict must contain: id (str), values (List[float]), metadata (Dict).
        """
        try:
            if not vectors:
                logger.warning("No vectors provided to upsert to Pinecone")
                return
            logger.debug(f"Upserting {len(vectors)} vectors into namespace '{namespace}'")
            self.index.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"Successfully upserted {len(vectors)} vectors to Pinecone")
        except Exception as e:
            logger.exception("Error upserting to Pinecone")
            raise

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def delete_namespace(self, namespace: str) -> None:
        """
        Deletes all vectors under the given namespace.
        """
        try:
            logger.debug(f"Deleting all vectors in namespace '{namespace}'")
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info(f"Namespace '{namespace}' cleared")
        except Exception as e:
            logger.exception("Error deleting namespace in Pinecone")
            raise

def get_pinecone_client() -> PineconeClient:
    """
    Factory method to create a singleton PineconeClient.
    """
    global _pinecone_client
    try:
        return _pinecone_client
    except NameError:
        _pinecone_client = PineconeClient()
        return _pinecone_client
from pydantic import AnyUrl, validator, Field
from pydantic_settings import BaseSettings
from typing import List, Dict
from functools import lru_cache
import os

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or .env file.
    Includes settings for messaging, discovery, storage, and external integrations.
    """
    # Kafka / Message bus configuration
    kafka_bootstrap_servers: List[str] = Field(..., env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic_analysis: str = Field("tasks.analysis", env="KAFKA_TOPIC_ANALYSIS")
    kafka_topic_planning: str = Field("tasks.planning", env="KAFKA_TOPIC_PLANNING")
    kafka_topic_blueprint: str = Field("tasks.blueprint", env="KAFKA_TOPIC_BLUEPRINT")
    kafka_topic_coding: str = Field("tasks.coding", env="KAFKA_TOPIC_CODING")
    kafka_topic_testing: str = Field("tasks.testing", env="KAFKA_TOPIC_TESTING")
    kafka_group_prefix: str = Field("agent-group", env="KAFKA_GROUP_PREFIX")

    # Redis Streams fallback
    redis_url: AnyUrl = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Swarm / Peer discovery
    swarm_seed_peers: List[str] = Field(default_factory=list, env="SWARM_SEED_PEERS")

    # Vector store (RAG)
    vector_db_url: AnyUrl = Field(..., env="VECTOR_DB_URL")
    vector_db_api_key: str = Field(..., env="VECTOR_DB_API_KEY")

    # Object store (S3/MinIO)
    s3_endpoint_url: AnyUrl = Field(..., env="S3_ENDPOINT_URL")
    s3_access_key: str = Field(..., env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(..., env="S3_SECRET_KEY")
    s3_bucket: str = Field(..., env="S3_BUCKET")

    # Persistence DB (optional)
    mongodb_uri: str = Field("mongodb://localhost:27017", env="MONGODB_URI")
    mongodb_db_name: str = Field("pipeline", env="MONGODB_DB_NAME")

    # GitHub integration
    github_repo: str = Field(..., env="GITHUB_REPO")
    github_token: str = Field(..., env="GITHUB_TOKEN")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("kafka_bootstrap_servers", pre=True)
    def _split_bootstrap_servers(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @validator("swarm_seed_peers", pre=True)
    def _split_swarm_peers(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve a singleton Settings instance.
    """
    return Settings()

def get_kafka_producer_config() -> Dict[str, str]:
    """
    Build Kafka producer configuration dict.
    """
    settings = get_settings()
    return {
        "bootstrap.servers": ",".join(settings.kafka_bootstrap_servers),
        "client.id": os.getenv("HOSTNAME", "agent-producer"),
        "acks": "all",
        "enable.idempotence": "true"
    }

def get_kafka_consumer_config(group_suffix: str) -> Dict[str, str]:
    """
    Build Kafka consumer configuration dict for a given group suffix.
    """
    settings = get_settings()
    group_id = f"{settings.kafka_group_prefix}.{group_suffix}"
    return {
        "bootstrap.servers": ",".join(settings.kafka_bootstrap_servers),
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": "false"
    }

def get_topic_map() -> Dict[str, str]:
    """
    Returns a mapping of pipeline stage names to Kafka topic names.
    """
    s = get_settings()
    return {
        "analysis": s.kafka_topic_analysis,
        "planning": s.kafka_topic_planning,
        "blueprint": s.kafka_topic_blueprint,
        "coding": s.kafka_topic_coding,
        "testing": s.kafka_topic_testing
    }

def get_redis_url() -> str:
    """
    Retrieve Redis connection URL.
    """
    return str(get_settings().redis_url)

def get_swarm_peers() -> List[str]:
    """
    Retrieve list of seed peers for swarm discovery.
    """
    return get_settings().swarm_seed_peers

def get_s3_config() -> Dict[str, str]:
    """
    Build S3 (or S3-compatible) object store configuration.
    """
    s = get_settings()
    return {
        "endpoint_url": str(s.s3_endpoint_url),
        "aws_access_key_id": s.s3_access_key,
        "aws_secret_access_key": s.s3_secret_key,
        "bucket": s.s3_bucket
    }

def get_vector_store_config() -> Dict[str, str]:
    """
    Build vector store configuration.
    """
    s = get_settings()
    return {
        "url": str(s.vector_db_url),
        "api_key": s.vector_db_api_key
    }

def get_mongodb_config() -> Dict[str, str]:
    """
    Build MongoDB configuration.
    """
    s = get_settings()
    return {
        "uri": s.mongodb_uri,
        "db_name": s.mongodb_db_name
    }

def get_github_config() -> Dict[str, str]:
    """
    Build GitHub integration configuration.
    """
    s = get_settings()
    return {
        "repo": s.github_repo,
        "token": s.github_token
    }
# app/core/weaviate_client.py
"""
Weaviate vector database client
"""

import json
from typing import Any, Dict, List, Optional

import weaviate

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.logging import logger
from app.core.retry import retry_weaviate


class WeaviateClient:
    """Weaviate client for vector operations"""

    def __init__(self):
        self.client = None
        self.class_name = settings.WEAVIATE_CLASS_NAME
        self._connect()

    def _connect(self):
        """Connect to Weaviate instance"""
        try:
            # Configure Weaviate client
            try:
                # Try v4 client first
                self.client = weaviate.connect_to_local(
                    host=settings.WEAVIATE_URL.replace("http://", "").replace(
                        "https://", ""
                    ),
                    port=8080,
                    grpc_port=50051,
                )
            except Exception:
                # Fallback to v3 client
                client_config = {
                    "url": settings.WEAVIATE_URL,
                }

                # Add API key if provided
                if settings.WEAVIATE_API_KEY:
                    client_config["auth_client_secret"] = weaviate.AuthApiKey(
                        api_key=settings.WEAVIATE_API_KEY
                    )

                self.client = weaviate.Client(**client_config)

            # Test connection
            if self.client.is_ready():
                logger.info(f"Connected to Weaviate at {settings.WEAVIATE_URL}")
                self._setup_schema()
            else:
                raise ExternalServiceException(
                    "Weaviate connection failed", service_name="weaviate"
                )

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {str(e)}")
            raise ExternalServiceException(
                f"Failed to connect to Weaviate: {str(e)}", service_name="weaviate"
            )

    def _setup_schema(self):
        try:
            if self.client.schema.exists(self.class_name):
                logger.info(f"Weaviate class '{self.class_name}' already exists")
                return

            class_schema = {
                "class": self.class_name,
                "description": "RAG documents for retrieval",
                "vectorizer": "text2vec-openai",
                "moduleConfig": {
                    "text2vec-openai": {
                        "model": "text-embedding-3-small",
                        "type": "text",
                    }
                },
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Document content",
                    },
                    {
                        "name": "source",
                        "dataType": ["string"],
                        "description": "Document source",
                    },
                    {
                        "name": "metadata_json",
                        "dataType": ["text"],
                        "description": "JSON-serialized metadata",
                    },
                    {
                        "name": "query_id",
                        "dataType": ["string"],
                        "description": "Related query ID",
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "Creation time",
                    },
                ],
            }
            self.client.schema.create_class(class_schema)
            logger.info(f"Created Weaviate class '{self.class_name}'")
        except Exception as e:
            logger.error(f"Failed to setup Weaviate schema: {str(e)}")
            raise ExternalServiceException(
                f"Failed to setup Weaviate schema: {str(e)}", service_name="weaviate"
            )

    def add_document(
        self,
        content: str,
        source: str,
        metadata: Dict[str, Any],
        query_id: Optional[str] = None,
    ) -> str:
        try:
            from datetime import datetime

            document_data = {
                "content": content,
                "source": source,
                "metadata_json": json.dumps(metadata, ensure_ascii=False),
                "query_id": query_id or "",
                "created_at": datetime.utcnow().isoformat(),
            }
            doc_uuid = self.client.data_object.create(
                data_object=document_data, class_name=self.class_name
            )
            logger.info(f"Added document to Weaviate with ID: {doc_uuid}")
            return doc_uuid
        except Exception as e:
            logger.error(f"Failed to add document to Weaviate: {str(e)}")
            raise ExternalServiceException(
                f"Failed to add document to Weaviate: {str(e)}", service_name="weaviate"
            )

    @retry_weaviate(max_attempts=3)
    def search_similar(
        self, query: str, top_k: int = 5, where_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        try:
            query_builder = (
                self.client.query.get(
                    self.class_name,
                    ["content", "source", "metadata_json", "query_id", "created_at"],
                )
                .with_near_text({"concepts": [query]})
                .with_limit(top_k)
                .with_additional(["id", "certainty", "distance"])
            )
            if where_filter:
                query_builder = query_builder.with_where(where_filter)

            result = query_builder.do()
            documents = []
            if "data" in result and "Get" in result["data"]:
                for item in result["data"]["Get"][self.class_name]:
                    md = {}
                    try:
                        md = json.loads(item.get("metadata_json") or "{}")
                    except Exception:
                        md = {}

                    documents.append(
                        {
                            "id": item["_additional"]["id"],
                            "content": item["content"],
                            "source": item["source"],
                            "metadata": md,
                            "query_id": item.get("query_id"),
                            "created_at": item.get("created_at"),
                            "certainty": item["_additional"]["certainty"],
                            "distance": item["_additional"]["distance"],
                        }
                    )
            logger.info(
                f"Found {len(documents)} similar documents for query: '{query[:50]}...'"
            )
            return documents
        except Exception as e:
            logger.error(f"Failed to search Weaviate: {str(e)}")
            raise ExternalServiceException(
                f"Failed to search Weaviate: {str(e)}", service_name="weaviate"
            )

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from Weaviate"""
        try:
            self.client.data_object.delete(uuid=document_id, class_name=self.class_name)
            logger.info(f"Deleted document from Weaviate with ID: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document from Weaviate: {str(e)}")
            raise ExternalServiceException(
                f"Failed to delete document from Weaviate: {str(e)}",
                service_name="weaviate",
            )

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            result = self.client.data_object.get_by_id(
                uuid=document_id, class_name=self.class_name
            )

            if result:
                return {
                    "id": result["id"],
                    "content": result["properties"]["content"],
                    "source": result["properties"]["source"],
                    "metadata": result["properties"]["metadata"],
                    "query_id": result["properties"]["query_id"],
                    "created_at": result["properties"]["created_at"],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get document from Weaviate: {str(e)}")
            raise ExternalServiceException(
                f"Failed to get document from Weaviate: {str(e)}",
                service_name="weaviate",
            )

    def health_check(self) -> bool:
        """Check Weaviate health"""
        try:
            return self.client.is_ready()
        except Exception as e:
            logger.error(f"Weaviate health check failed: {str(e)}")
            return False


# Global Weaviate client instance
weaviate_client = WeaviateClient()

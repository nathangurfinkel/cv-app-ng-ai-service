"""
Vectorstore service for document storage and retrieval.
Cloud-native implementation using Pinecone directly (no LangChain overhead).
"""
from typing import List, Optional, Dict, Any
import openai
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from ..core.config import settings
from ..utils.debug import print_step

class VectorstoreService:
    """Service for vectorstore operations."""
    
    def __init__(self):
        """Initialize the vectorstore service."""
        self.pinecone_client: Optional[PineconeClient] = None
        self.index = None
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize Pinecone client and index."""
        print_step("Pinecone Initialization", {
            "api_key_present": bool(settings.PINECONE_API_KEY)
        }, "input")
        
        if not settings.PINECONE_API_KEY:
            print_step("Pinecone Initialization", 
                      "Pinecone not initialized - API key required", "error")
            return
        
        try:
            self.pinecone_client = PineconeClient(api_key=settings.PINECONE_API_KEY)
            existing_indexes = self.pinecone_client.list_indexes().names()
            
            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                print_step("Pinecone Index Creation", {
                    "index_name": settings.PINECONE_INDEX_NAME,
                    "dimension": 1536
                }, "input")
                
                self.pinecone_client.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=1536,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
                print_step("Pinecone Index Creation", 
                          f"Index '{settings.PINECONE_INDEX_NAME}' created successfully", "output")
            
            self.index = self.pinecone_client.Index(settings.PINECONE_INDEX_NAME)
            print_step("Pinecone Initialization", 
                      "Pinecone client and index initialized successfully", "output")
            
        except Exception as e:
            print_step("Pinecone Initialization", 
                      f"Failed to initialize Pinecone: {str(e)}", "error")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print_step("Embedding Generation", f"Failed to generate embedding: {str(e)}", "error")
            raise
    
    def _split_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Simple text splitter without LangChain dependency."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                # Try to split at sentence boundary
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                split_point = max(last_period, last_newline)
                if split_point > start:
                    end = split_point + 1
            
            chunks.append(text[start:end].strip())
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def add_documents(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> None:
        """
        Add documents to vectorstore.
        
        Args:
            texts: List of texts to add
            metadata: Optional metadata for each text
        """
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        
        if metadata is None:
            metadata = [{}] * len(texts)
        
        print_step("Document Indexing", {
            "document_count": len(texts)
        }, "input")
        
        vectors = []
        for i, text in enumerate(texts):
            # Split text into chunks
            chunks = self._split_text(text)
            for j, chunk in enumerate(chunks):
                embedding = self._get_embedding(chunk)
                vectors.append({
                    'id': f"doc_{i}_chunk_{j}",
                    'values': embedding,
                    'metadata': {
                        **metadata[i],
                        'text': chunk,
                        'chunk_index': j,
                        'total_chunks': len(chunks)
                    }
                })
        
        # Upsert to Pinecone
        self.index.upsert(vectors=vectors)
        print_step("Document Indexing", f"Added {len(vectors)} vectors to Pinecone", "output")
    
    def retrieve_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents from vectorstore.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            Retrieved documents with metadata
        """
        if not self.index:
            raise ValueError("Pinecone index not initialized")
        
        print_step("Document Retrieval", {
            "query": query,
            "k": k
        }, "input")
        
        query_embedding = self._get_embedding(query)
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True
        )
        
        retrieved_docs = []
        for match in results.matches:
            retrieved_docs.append({
                'text': match.metadata.get('text', ''),
                'score': match.score,
                'metadata': match.metadata
            })
        
        print_step("Document Retrieval", {
            "retrieved_docs_count": len(retrieved_docs),
            "retrieved_context_length": sum(len(doc['text']) for doc in retrieved_docs)
        }, "output")
        
        return retrieved_docs
    
    def clear_vectorstore(self) -> None:
        """Clear all documents from vectorstore."""
        if not self.index:
            return
        
        print_step("Vectorstore Cleanup", 
                  "Pinecone cleanup not supported in production", "info")
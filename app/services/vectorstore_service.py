"""
Vectorstore service for document storage and retrieval.
"""
from typing import List, Optional
from langchain_pinecone import PineconeVectorStore
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from ..core.config import settings
from ..utils.debug import print_step

class VectorstoreService:
    """Service for vectorstore operations."""
    
    def __init__(self):
        """Initialize the vectorstore service."""
        self.embeddings: Optional[OpenAIEmbeddings] = None
        self.vectorstore: Optional[PineconeVectorStore] = None
        self.text_splitter: RecursiveCharacterTextSplitter = None
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize embeddings, text splitter, and vectorstore."""
        # Initialize embeddings
        print_step("Embeddings Initialization", {
            "api_key_present": bool(settings.OPENAI_API_KEY)
        }, "input")
        
        if settings.OPENAI_API_KEY:
            self.embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
            print_step("Embeddings Initialization", 
                      "OpenAI embeddings initialized successfully", "output")
        else:
            print_step("Embeddings Initialization", 
                      "OpenAI embeddings not available - API key required", "error")
        
        # Initialize text splitter
        print_step("Text Splitter Setup", {
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP
        }, "input")
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        print_step("Text Splitter Setup", "Text splitter initialized", "output")
        
        # Initialize vectorstore
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self) -> None:
        """Initialize the vectorstore."""
        print_step("Vectorstore Initialization", {
            "embeddings_available": self.embeddings is not None,
            "mock_pinecone": settings.MOCK_PINECONE
        }, "input")
        
        if not self.embeddings:
            print_step("Vectorstore Initialization", 
                      "Vectorstore not initialized - OpenAI API key required", "error")
            return
        
        if settings.MOCK_PINECONE:
            print_step("Vectorstore Initialization", 
                      "Using mocked Pinecone (ChromaDB in-memory)", "info")
            self.vectorstore = Chroma(
                embedding_function=self.embeddings,
                collection_name=settings.PINECONE_INDEX_NAME
            )
            print_step("Vectorstore Initialization", 
                      "ChromaDB vectorstore created", "output")
        else:
            self._initialize_pinecone()
    
    def _initialize_pinecone(self) -> None:
        """Initialize Pinecone vectorstore."""
        print_step("Vectorstore Initialization", 
                  "Connecting to production Pinecone", "info")
        
        pinecone_client = PineconeClient(api_key=settings.PINECONE_API_KEY)
        existing_indexes = pinecone_client.list_indexes().names()
        print_step("Pinecone Index Check", {
            "existing_indexes": existing_indexes
        }, "info")
        
        if settings.PINECONE_INDEX_NAME not in existing_indexes:
            print_step("Pinecone Index Creation", {
                "index_name": settings.PINECONE_INDEX_NAME,
                "dimension": 1536
            }, "input")
            
            pinecone_client.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=1536,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            print_step("Pinecone Index Creation", 
                      f"Index '{settings.PINECONE_INDEX_NAME}' created successfully", "output")
        
        # Use the new langchain-pinecone package
        self.vectorstore = PineconeVectorStore.from_existing_index(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=self.embeddings
        )
        print_step("Vectorstore Initialization", 
                  "Pinecone vectorstore connected", "output")
    
    def create_documents(self, text: str) -> List[Document]:
        """
        Create documents from text.
        
        Args:
            text: Text to split into documents
            
        Returns:
            List of documents
        """
        print_step("Document Creation", {
            "text_length": len(text)
        }, "input")
        
        docs = self.text_splitter.create_documents([text])
        print_step("Document Creation", {
            "document_count": len(docs),
            "total_chunks": sum(len(doc.page_content) for doc in docs)
        }, "output")
        
        return docs
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to vectorstore.
        
        Args:
            documents: Documents to add
        """
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
            
        print_step("Document Indexing", {
            "document_count": len(documents)
        }, "input")
        
        self.vectorstore.add_documents(documents)
        print_step("Document Indexing", "Documents added to vectorstore", "output")
    
    def retrieve_documents(self, query: str, k: int = None) -> List[Document]:
        """
        Retrieve documents from vectorstore.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            Retrieved documents
        """
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
            
        k = k or settings.RETRIEVAL_K
        
        print_step("Document Retrieval", {
            "query": query,
            "k": k
        }, "input")
        
        retriever = self.vectorstore.as_retriever(search_kwargs={'k': k})
        retrieved_docs = retriever.invoke(query)
        
        print_step("Document Retrieval", {
            "retrieved_docs_count": len(retrieved_docs),
            "retrieved_context_length": sum(len(doc.page_content) for doc in retrieved_docs),
            "retrieved_context_preview": retrieved_docs[0].page_content[:200] + "..." if retrieved_docs else ""
        }, "output")
        
        return retrieved_docs
    
    def clear_vectorstore(self) -> None:
        """Clear all documents from vectorstore."""
        if not self.vectorstore:
            return
            
        print_step("Vectorstore Cleanup", {
            "mock_pinecone": settings.MOCK_PINECONE
        }, "input")
        
        if settings.MOCK_PINECONE and hasattr(self.vectorstore, '_collection'):
            collection_ids = self.vectorstore.get()['ids']
            if collection_ids:
                self.vectorstore._collection.delete(ids=collection_ids)
                print_step("Vectorstore Cleanup", {
                    "deleted_ids_count": len(collection_ids)
                }, "output")
            else:
                print_step("Vectorstore Cleanup", 
                          "No existing documents to delete", "output")
        else:
            print_step("Vectorstore Cleanup", 
                      "Vectorstore cleanup not supported for production Pinecone", "info")

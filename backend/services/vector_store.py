import chromadb
import uuid
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import json
import os
from pathlib import Path

class VectorStore:
    def __init__(self, persist_directory: str = "chroma_db"):
            """Initialize ChromaDB with sentence transformers"""
            self.persist_directory = Path(persist_directory)
            self.persist_directory.mkdir(exist_ok=True)
            
            # Initialize ChromaDB client
            self._init_client()
            
            print(f"✅ Vector store initialized with {self.collection.count()} existing chunks")
        
    def _init_client(self):
        """Initialize or reinitialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document chunks for RAG"}
        )
    
    def refresh_client(self):
        """Refresh the ChromaDB client to pick up latest data"""
        try:
            print("🔄 Refreshing vector store client...")
            
            # Clear any cached data
            if hasattr(self.client, 'clear_system_cache'):
                self.client.clear_system_cache()
            
            # Reinitialize client and collection
            self._init_client()
            
            chunk_count = self.collection.count()
            print(f"✅ Vector store refreshed with {chunk_count} total chunks")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not refresh vector store: {e}")
            # Fallback: just reinitialize
            self._init_client()
                    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for texts"""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()
    
    # Update the store_document_chunks method to add debugging
    async def store_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store document chunks in vector database and refresh client"""
        try:
            print(f"📦 Storing {len(chunks)} chunks for document {document_id}")
            
            if len(chunks) == 0:
                raise Exception("Cannot store empty chunks list")
            
            chunk_ids = []
            texts = []
            metadatas = []
            
            for chunk in chunks:
                if not chunk.get('content', '').strip():
                    print(f"⚠️ Skipping empty chunk at index {chunk.get('chunk_index', 'unknown')}")
                    continue
                    
                chunk_id = f"{document_id}_{chunk['chunk_index']}"
                chunk_ids.append(chunk_id)
                texts.append(chunk['content'])
                
                # Prepare metadata (ChromaDB requires string values)
                metadata = {
                    "document_id": document_id,
                    "chunk_index": str(chunk['chunk_index']),
                    "token_count": str(chunk['token_count']),
                    "filename": chunk['metadata']['filename'],
                    "total_chunks": str(chunk['metadata']['total_chunks']),
                    "extraction_method": chunk['metadata']['method']
                }
                
                # Add file-specific metadata
                if 'pages' in chunk['metadata']:
                    metadata['pages'] = str(chunk['metadata']['pages'])
                if 'paragraphs' in chunk['metadata']:
                    metadata['paragraphs'] = str(chunk['metadata']['paragraphs'])
                if 'slides' in chunk['metadata']:
                    metadata['slides'] = str(chunk['metadata']['slides'])
                if 'sheets' in chunk['metadata']:
                    metadata['sheets'] = str(chunk['metadata']['sheets'])
                
                metadatas.append(metadata)
            
            if len(texts) == 0:
                raise Exception("No valid text chunks found for embedding")
            
            print(f"🔤 Processing {len(texts)} text chunks for embedding")
            
            # Create embeddings
            print("🧠 Generating embeddings...")
            embeddings = self.create_embeddings(texts)
            
            if len(embeddings) == 0:
                raise Exception("Embedding generation failed - empty embeddings returned")
            
            print(f"✅ Generated {len(embeddings)} embeddings")
            
            # Store in ChromaDB
            self.collection.add(
                ids=chunk_ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            print(f"✅ Stored {len(chunks)} chunks for document {document_id}")
            
            # CRITICAL: Refresh the client after adding new documents
            self.refresh_client()
            
            return {
                "success": True,
                "chunks_stored": len(texts),
                "document_id": document_id
            }
        
        except Exception as e:
            print(f"❌ Error storing chunks: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_similar_chunks(
        self, 
        query: str, 
        document_ids: Optional[List[str]] = None, 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks with enhanced debugging"""
        try:
            print(f"🔍 Vector Store: Searching for query '{query}' with max_results={max_results}")
            
            # Create query embedding
            query_embedding = self.create_embeddings([query])
            if not query_embedding:
                print("❌ Vector Store: Failed to create query embedding")
                return []
            
            print(f"✅ Vector Store: Created embedding for query")
            
            # Prepare search filters
            where_clause = None
            if document_ids:
                where_clause = {"document_id": {"$in": document_ids}}
                print(f"🔍 Vector Store: Filtering by document_ids: {document_ids}")
            
            # Query the collection
            print(f"🔍 Vector Store: Querying collection with {len(query_embedding)} embeddings...")
            
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=max_results,
                where=where_clause,
                include=['metadatas', 'documents', 'distances']
            )
            
            print(f"📝 Vector Store: Raw query results: {type(results)}")
            if results:
                print(f"📝 Vector Store: Results keys: {results.keys()}")
                if 'documents' in results:
                    print(f"📝 Vector Store: Found {len(results['documents'][0]) if results['documents'] else 0} documents")
            
            # Process results
            if not results or not results.get('documents') or not results['documents'][0]:
                print("❌ Vector Store: No documents returned from query")
                return []
            
            processed_results = []
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            ids = results.get('ids', [[]])[0]
            
            print(f"✅ Vector Store: Processing {len(documents)} results...")
            
            for i in range(len(documents)):
                try:
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    chunk_id = ids[i] if i < len(ids) else f"chunk_{i}"
                    
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = max(0, 1 - distance)
                    
                    processed_result = {
                        "chunk_id": chunk_id,
                        "content": documents[i],
                        "similarity_score": similarity_score,
                        "metadata": metadata
                    }
                    
                    processed_results.append(processed_result)
                    print(f"✅ Vector Store: Result {i+1}: score={similarity_score:.3f}, source={metadata.get('filename', 'Unknown')}")
                    
                except Exception as e:
                    print(f"⚠️ Vector Store: Error processing result {i}: {e}")
                    continue
            
            print(f"✅ Vector Store: Returning {len(processed_results)} processed results")
            return processed_results
            
        except Exception as e:
            print(f"❌ Vector Store: Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """Get information about a stored document"""
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                metadata = results['metadatas'][0]
                return {
                    "document_id": document_id,
                    "filename": metadata.get('filename', 'Unknown'),
                    "total_chunks": int(metadata.get('total_chunks', 0)),
                    "extraction_method": metadata.get('extraction_method', 'Unknown'),
                    "exists": True
                }
            else:
                return {"document_id": document_id, "exists": False}
        
        except Exception as e:
            print(f"❌ Error getting document info: {e}")
            return {"document_id": document_id, "exists": False, "error": str(e)}
    
    def list_stored_documents(self) -> List[Dict[str, Any]]:
        """List all stored documents"""
        try:
            # Get all chunks
            results = self.collection.get()
            
            # Group by document_id
            documents = {}
            for i, chunk_id in enumerate(results['ids']):
                metadata = results['metadatas'][i]
                doc_id = metadata['document_id']
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": metadata.get('filename', 'Unknown'),
                        "total_chunks": int(metadata.get('total_chunks', 0)),
                        "extraction_method": metadata.get('extraction_method', 'Unknown')
                    }
            
            return list(documents.values())
        
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"🗑️ Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            else:
                print(f"⚠️ No chunks found for document {document_id}")
                return False
        
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
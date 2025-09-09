from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
from pathlib import Path
import mimetypes
from datetime import datetime

from models.document_models import (
    DocumentUploadResponse, 
    DocumentQuery, 
    DocumentSearchResult
)
from services.document_processor import DocumentProcessor
from services.vector_store import VectorStore

router = APIRouter()

# Initialize services
document_processor = DocumentProcessor()
vector_store = VectorStore()

@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check if file type is supported
        if not document_processor.is_supported_file(file.filename):
            supported = document_processor.get_supported_extensions()
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported: {supported}"
            )
        
        # Check file size (limit to 50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
            )
        
        print(f"📄 Processing document: {file.filename} ({len(file_content)} bytes)")
        
        # Save file
        document_id, file_path = await document_processor.save_uploaded_file(
            file_content, file.filename
        )
        
        # Process document
        processed_result = await document_processor.process_document(
            file_path, file.filename
        )
        
        # Store in vector database
        store_result = await vector_store.store_document_chunks(
            document_id, processed_result["chunks"]
        )
        
        if not store_result["success"]:
            # Clean up file if vector storage failed
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to store document: {store_result['error']}")
        
        print(f"✅ Document processed successfully: {document_id}")

        # IMPORTANT: Refresh any existing RAG service instances
        # This ensures subsequent queries use the updated vector store
        try:
            from services.rag_service import RAGService
            # Create a temporary RAG service to refresh vector store
            temp_rag = RAGService()
            temp_rag.refresh_vector_store()
            print("🔄 Refreshed RAG service with new document")
        except Exception as e:
            print(f"⚠️ Warning: Could not refresh RAG service: {e}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type or "unknown",
            status="success",
            upload_time=datetime.now(),
            total_chunks=processed_result["total_chunks"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/search-documents")
async def search_documents(query_data: DocumentQuery):
    """Search for relevant document chunks"""
    try:
        results = await vector_store.search_similar_chunks(
            query=query_data.query,
            document_ids=query_data.document_ids,
            max_results=query_data.max_chunks
        )
        
        formatted_results = [
            DocumentSearchResult(
                chunk_id=result["chunk_id"],
                content=result["content"],
                similarity_score=result["similarity_score"],
                metadata=result["metadata"],
                page_number=int(result["metadata"].get("page_number", 0)) if result["metadata"].get("page_number") else None
            )
            for result in results
        ]
        
        return {
            "success": True,
            "query": query_data.query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
    
    except Exception as e:
        print(f"❌ Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/list-documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents = vector_store.list_stored_documents()
        return {
            "success": True,
            "documents": documents,
            "total_documents": len(documents)
        }
    except Exception as e:
        print(f"❌ Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@router.get("/document-info/{document_id}")
async def get_document_info(document_id: str):
    """Get information about a specific document"""
    try:
        info = vector_store.get_document_info(document_id)
        return info
    except Exception as e:
        print(f"❌ Error getting document info: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting document info: {str(e)}")

@router.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    try:
        success = vector_store.delete_document(document_id)
        
        if success:
            # Also try to delete the original file
            try:
                upload_dir = Path("uploads")
                for file_path in upload_dir.glob(f"{document_id}.*"):
                    os.remove(file_path)
                    print(f"🗑️ Deleted file: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not delete original file: {e}")
            
            return {"success": True, "message": "Document deleted successfully"}
        else:
            return {"success": False, "message": "Document not found"}
    
    except Exception as e:
        print(f"❌ Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@router.get("/health-documents")
async def health_check():
    """Health check for document service"""
    try:
        # Test vector store
        document_count = len(vector_store.list_stored_documents())
        
        return {
            "status": "healthy",
            "service": "documents",
            "stored_documents": document_count,
            "supported_formats": document_processor.get_supported_extensions()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "documents",
            "error": str(e)
        }
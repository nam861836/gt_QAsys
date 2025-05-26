from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import os
from dotenv import load_dotenv

from database import get_db, engine
from models import Base, User, ChatHistory, Document
from schemas import (
    UserCreate, UserResponse, Token, ChatMessage, ChatResponse,
    ChatHistoryResponse, DocumentResponse, WebSearchResult, WeatherInfo
)
from utils import (
    verify_password, get_password_hash, create_access_token,
    verify_token, process_file_content
)
from rag import process_document, retrieve_relevant_chunks, delete_document_chunks
from tools import web_search, get_weather, format_weather_context, format_web_search_context
from retrieval_and_generation.answer_generator import generate_answer_with_openai as generate_answer_with_context, generate_chat_response

# Create database tables
Base.metadata.create_all(bind=engine)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Chat Application")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependencies
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token)
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

# Authentication routes
@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Chat routes
@app.post("/chat/message", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if message.chat_type == "document_qa":
            # Get relevant chunks from documents
            relevant_chunks = retrieve_relevant_chunks(message.message, current_user.id)
            if not relevant_chunks:
                return ChatResponse(
                    response="Xin lỗi, tôi không tìm thấy thông tin liên quan trong tài liệu.",
                    chat_type="document_qa"
                )
            
            # Format context from chunks
            context = "\n\n".join([chunk["text"] for chunk in relevant_chunks])
            
            # Generate answer using OpenAI with context
            response = generate_answer_with_context(message.message, context)
        else:
            # Regular chat using OpenAI
            response = generate_chat_response(message.message)

        # Save chat history
        chat_history = ChatHistory(
            user_id=current_user.id,
            message=message.message,
            response=response,
            chat_type=message.chat_type
        )
        db.add(chat_history)
        db.commit()

        return ChatResponse(response=response, chat_type=message.chat_type)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/chat/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat_history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == current_user.id)\
        .order_by(ChatHistory.created_at.desc())\
        .all()
    return chat_history

# Document routes
@app.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Read file content
        content = await file.read()
        
        # Process file content based on type
        file_type = file.filename.split(".")[-1].lower()
        if file_type not in ["pdf", "docx", "txt"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type"
            )
        
        text_content = process_file_content(content, file_type)
        
        # Create document record
        document = Document(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file_type,
            content=text_content
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        try:
            # Process document for RAG
            process_document(text_content, current_user.id, document.id)
        except Exception as rag_error:
            print(f"Error processing document for RAG: {str(rag_error)}")
            # Don't raise the error, just log it and continue
            # The document is still saved in the database
        
        return document
    except Exception as e:
        print(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    documents = db.query(Document)\
        .filter(Document.user_id == current_user.id)\
        .order_by(Document.created_at.desc())\
        .all()
    return documents

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # First, get the document to verify ownership
        document = db.query(Document)\
            .filter(Document.id == document_id, Document.user_id == current_user.id)\
            .first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        try:
            # Delete document chunks from Qdrant
            delete_document_chunks(current_user.id, document_id)
        except Exception as qdrant_error:
            print(f"Error deleting document chunks from Qdrant: {str(qdrant_error)}")
            # Continue with database deletion even if Qdrant deletion fails
        
        # Delete document from database
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

# Tool routes
@app.get("/tools/search", response_model=List[WebSearchResult])
async def search_web(
    query: str,
    num_results: int = 5,
    current_user: User = Depends(get_current_user)
):
    results = web_search(query, num_results)
    return results

@app.get("/tools/weather", response_model=WeatherInfo)
async def get_weather_info(
    city: str,
    current_user: User = Depends(get_current_user)
):
    weather_info = get_weather(city)
    if not weather_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found"
        )
    return weather_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
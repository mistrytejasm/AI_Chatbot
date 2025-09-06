from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.chat import router as chat_router
from core.config import settings

def create_application() -> FastAPI:
    app = FastAPI(
        title="Perplexity 2.0 API",
        description="Advanced AI Chat Assistant with Web Search",
        version="2.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers WITHOUT prefix to match frontend
    app.include_router(chat_router)

    @app.get("/")
    async def root():
        return {
            "message": "Perplexity 2.0 API is running",
            "status": "healthy",
            "version": "2.0.0"
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_application()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Perplexity 2.0 API server...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

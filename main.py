import uvicorn
from api import app

if __name__ == "__main__":
    # Run FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Auto-reload on code changes (dev only)
    )
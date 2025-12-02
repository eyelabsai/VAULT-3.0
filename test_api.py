"""
Test the FastAPI backend locally before deploying to Vercel
Run with: python test_api.py
"""

import uvicorn
from api.predict import app

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Starting Vault 3.0 API Server for Testing")
    print("="*70)
    print("\nAPI will be available at:")
    print("  - http://localhost:8000")
    print("  - Docs: http://localhost:8000/docs")
    print("\nFrontend (open in browser):")
    print("  - file:///Users/gurpalvirdi/Vault%203.0/public/index.html")
    print("\nPress Ctrl+C to stop")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)


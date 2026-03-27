"""
NL2SQL Compiler - Main Entry Point

Run this file to start the application.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()


def main():
    """Run the NL2SQL Compiler application."""
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    print("=" * 50)
    print("🚀 NL2SQL Compiler - Agentic AI")
    print("=" * 50)
    print(f"📍 Starting server at http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print("=" * 50)
    
    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()

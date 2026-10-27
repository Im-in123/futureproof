"""Run the FutureProof web server."""
import sys
from pathlib import Path

# Ensure the project root is importable, regardless of CWD
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.api.server:app", host="127.0.0.1", port=9090, log_level="warning")

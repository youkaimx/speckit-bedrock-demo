"""Run entrypoint for the API: parses --log-level and starts uvicorn.

When --log-level is set, it overrides LOG_LEVEL from .env/config (plan Logging).
Usage: python -m src.api.run [--log-level DEBUG] [--host 0.0.0.0] [--port 8000] [--reload].
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Document RAG API with optional --log-level (overrides LOG_LEVEL from config)."
    )
    parser.add_argument(
        "--log-level",
        metavar="LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity (overrides LOG_LEVEL from .env); default from config.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload")
    args = parser.parse_args()

    if args.log_level is not None:
        os.environ["LOG_LEVEL"] = args.log_level

    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
    sys.exit(0)

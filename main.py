#!/usr/bin/env python3
"""
Dropsy OSINT: Universal Launcher.
Runs the Web Platform, Terminal Demonstration, or Unit Test Suite.
"""

import sys, os
import argparse
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    print("[*] Running Dropsy AI Unit & Integration Tests...")
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(os.path.dirname(__file__), "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    print(f"\n[*] Launching Dropsy OSINT Investigation Platform...")
    print(f"[*] Audit console: http://{host}:{port}/audit")
    print(f"[*] Interactive API Docs: http://{host}:{port}/docs\n")
    uvicorn.run("dropsy.api.server:app", host=host, port=port, reload=True, log_level="info")


def run_cli_demo():
    from dropsy.cli import run_dropsy_cli_demo
    run_dropsy_cli_demo()


def main():
    parser = argparse.ArgumentParser(description="Dropsy - Autonomous AI OSINT Threat Intelligence System")
    parser.add_argument("--server", action="store_true", help="Launch FastAPI web server and UI (Default)")
    parser.add_argument("--cli", action="store_true", help="Run terminal investigation demo")
    parser.add_argument("--demo", action="store_true", help="Run the AI Fundamentals DarkPhish benchmark")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host (default: 127.0.0.1)")

    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.demo:
        from dropsy.core.darkphish_course import print_summary
        print_summary()
    elif args.cli:
        run_cli_demo()
    else:
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

# Export app for Vercel / ASGI serverless
import os
os.environ.setdefault('DROPSY_HISTORY_DB', '/tmp/history.sqlite3')
from dropsy.api.server import app

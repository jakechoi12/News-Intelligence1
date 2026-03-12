#!/usr/bin/env python3
"""
로컬에서 프론트엔드를 HTTP로 서빙합니다.
브라우저에서 http://localhost:8000 으로 접속해 배포 없이 테스트할 수 있습니다.

사용법 (프로젝트 루트에서):
  python serve_local.py

데이터 갱신이 필요하면 먼저 실행:
  python backend/run_collection.py
"""
import http.server
import os
import socketserver
import webbrowser
from pathlib import Path

PORT = 8001
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


def main():
    os.chdir(FRONTEND_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"로컬 서버: {url}")
        print("종료하려면 Ctrl+C")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()


if __name__ == "__main__":
    main()

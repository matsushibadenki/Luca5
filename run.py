# /run.py
# title: アプリケーション起動スクリプト
# role: Uvicornサーバーを2つ（メインAPIとアナリティクス）起動するエントリーポイント。

import uvicorn
import logging
import multiprocessing
from app.config import settings

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_main_server() -> None:
    """ポート8000でメインのFastAPIアプリケーションを起動する"""
    logger.info(f"Starting main API server on http://{settings.HOST}:{settings.PORT}")
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

def run_analytics_server() -> None:
    """ポート8001でアナリティクス用のFastAPIアプリケーションを起動する"""
    logger.info(f"Starting analytics server on http://{settings.HOST}:{settings.ANALYTICS_PORT}")
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    uvicorn.run(
        "app.main:analytics_app",
        host=settings.HOST,
        port=settings.ANALYTICS_PORT,
        log_level="info"
    )
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

if __name__ == "__main__":
    logger.info("Starting Luca5 server processes...")

    # メインサーバーとアナリティクスサーバーを別々のプロセスで起動
    main_process = multiprocessing.Process(target=run_main_server)
    analytics_process = multiprocessing.Process(target=run_analytics_server)

    try:
        main_process.start()
        analytics_process.start()
        main_process.join()
        analytics_process.join()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Terminating processes.")
        main_process.terminate()
        analytics_process.terminate()
        main_process.join()
        analytics_process.join()
        logger.info("Processes terminated.")
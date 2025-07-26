# /app/main.py
# title: FastAPIアプリケーションのメインファイル
# role: FastAPIアプリケーションのインスタンスを作成し、APIルーター、イベントハンドラ、ミドルウェアを設定する。

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dependency_injector.wiring import inject, Provide

# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
from app.api import router as api_router
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
from app.analytics.router import router as analytics_router
from app.containers import Container, wire_circular_dependencies
from app.sandbox.sandbox_manager import SandboxManager

logger = logging.getLogger(__name__)

@asynccontextmanager
@inject
async def lifespan(
    app: FastAPI, 
    sandbox_manager: SandboxManager = Provide[Container.sandbox_manager]
):
    """
    FastAPIアプリケーションのライフサイクルを管理する。
    起動時にサンドボックスを開始し、終了時に停止する。
    """
    # アプリケーション起動時の処理
    logger.info("Application startup...")
    logger.info("Starting sandbox environment...")
    try:
        # Dockerイメージをリビルドしてクリーンな状態から開始
        sandbox_manager.build_image()
        sandbox_manager.rebuild_sandbox()
        logger.info("Sandbox environment started successfully.")
    except Exception as e:
        logger.error(f"Failed to start sandbox environment during startup: {e}", exc_info=True)
    
    yield
    
    # アプリケーション終了時の処理
    logger.info("Application shutdown...")
    logger.info("Stopping sandbox environment...")
    try:
        sandbox_manager.stop_sandbox()
        logger.info("Sandbox environment stopped successfully.")
    except Exception as e:
        logger.error(f"Failed to stop sandbox environment during shutdown: {e}", exc_info=True)


# DIコンテナのセットアップ
container = Container()
wire_circular_dependencies(container)
# FastAPIのエンドポイント関数がDIコンテナを使えるようにする
container.wire(modules=[__name__, "app.api", "app.analytics.router"])

# メインAPI用のFastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="Luca5 - An Advanced Cognitive Architecture",
    description="An AI system with self-improvement and sandbox capabilities.",
    version="1.0.0",
    lifespan=lifespan
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターの組み込み
app.include_router(api_router, prefix="/api/v1")

# Analyticsサーバー用のFastAPIアプリケーションのインスタンスを作成
analytics_app = FastAPI(title="Luca5 Analytics")
analytics_app.include_router(analytics_router)
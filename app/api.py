# /app/api.py
# title: APIエンドポイント定義
# role: ユーザーとの対話を受け付けるFastAPIのエンドポイントを定義する。

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
import logging

from app.containers import Container
from app.engine import MetaIntelligenceEngine
from app.models import ChatRequest, ChatResponse, OrchestrationDecision
from app.agents import OrchestrationAgent

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    engine: MetaIntelligenceEngine = Depends(Provide[Container.engine]),
    orchestration_agent: OrchestrationAgent = Depends(Provide[Container.orchestration_agent]),
):
    """
    ユーザーからのクエリを受け取り、AIエンジンで処理して応答を返す。
    """
    try:
        input_data = {"query": request.query, "affective_state": None}
        orchestration_decision = await orchestration_agent.arun(input_data)

        response_data = await engine.arun(request.query, orchestration_decision)
        
        return ChatResponse(**response_data.model_dump())

    except Exception as e:
        logger.error(f"チャットリクエストの処理中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"内部サーバーエラー: {str(e)}"
        )
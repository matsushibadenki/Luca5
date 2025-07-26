# /app/models/__init__.py
# title: Pydanticモデル定義
# role: アプリケーション全体で使用されるデータ構造をPydanticモデルとして定義する。

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ToolCall(BaseModel):
    """
    思考プロセスにおけるツール呼び出しの構造を定義するモデル。
    """
    tool_name: str
    tool_input: str

class ThoughtProcess(BaseModel):
    """
    思考の連鎖（Chain of Thought）の各ステップを表現するモデル。
    """
    thought: str
    tool_calls: List[ToolCall] = []

class OrchestrationDecision(BaseModel):
    """
    OrchestrationAgentの出力を定義するモデル。
    どのパイプラインを選択すべきか、その理由などを格納する。
    """
    reasoning: str
    chosen_mode: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    parameters: Dict[str, Any] = {}

class MasterAgentResponse(BaseModel):
    """
    MasterAgentからの最終的な応答の構造を定義するモデル。
    """
    final_answer: str
    self_criticism: str
    potential_problems: str
    retrieved_info: str

# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
class ChatRequest(BaseModel):
    """
    /chatエンドポイントへのリクエストボディのモデル。
    """
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    """
    /chatエンドポイントからのレスポンスボディのモデル。
    MasterAgentResponseの構造を継承・利用する。
    """
    final_answer: str
    self_criticism: str
    potential_problems: str
    retrieved_info: str
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
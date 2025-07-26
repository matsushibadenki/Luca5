# /app/agents/speculative_correction_agent.py
# title: 推測的修正AIエージェント
# role: コードの問題点を推測し、大胆な修正案を生成する。コード生成に特化したCodestralモデルを利用する。

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from typing import Any, Dict

from app.agents.base import AIAgent

class SpeculativeCorrectionAgent(AIAgent):
    """
    コードの修正案を推測に基づいて生成するAIエージェント。
    """
    def __init__(self, llm: Any, output_parser: Any, prompt_template: ChatPromptTemplate):
        self.llm = llm
        self.output_parser = output_parser
        self.prompt_template = prompt_template
        super().__init__()

    def build_chain(self) -> Runnable:
        """
        推測的修正エージェントのLangChainチェーンを構築します。
        """
        return self.prompt_template | self.llm | self.output_parser

    def invoke(self, input_data: Dict[str, Any] | str) -> str:
        if not isinstance(input_data, dict):
            raise TypeError("SpeculativeCorrectionAgent expects a dictionary as input.")
        
        if self._chain is None:
            raise RuntimeError("SpeculativeCorrectionAgent's chain is not initialized.")
        
        result: str = self._chain.invoke(input_data)
        return result
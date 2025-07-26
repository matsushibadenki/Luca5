# /app/agents/step_by_step_verifier_agent.py
# title: ステップバイステップ検証AIエージェント
# role: 提案されたコード修正案を、元のコードと比較しながら論理的に検証し、問題点を指摘する。

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser
from typing import Any, Dict

from app.agents.base import AIAgent

class StepByStepVerifierAgent(AIAgent):
    """
    コード修正案をステップバイステップで検証するAIエージェント。
    """
    def __init__(self, llm: Any, output_parser: JsonOutputParser, prompt_template: ChatPromptTemplate):
        self.llm = llm
        self.output_parser = output_parser
        self.prompt_template = prompt_template
        super().__init__()

    def build_chain(self) -> Runnable:
        """
        ステップバイステップ検証エージェントのLangChainチェーンを構築します。
        """
        return self.prompt_template | self.llm | self.output_parser

    def invoke(self, input_data: Dict[str, Any] | str) -> Dict[str, Any]:
        if not isinstance(input_data, dict):
            raise TypeError("StepByStepVerifierAgent expects a dictionary as input.")
        
        if self._chain is None:
            raise RuntimeError("StepByStepVerifierAgent's chain is not initialized.")
        
        result: Dict[str, Any] = self._chain.invoke(input_data)
        return result
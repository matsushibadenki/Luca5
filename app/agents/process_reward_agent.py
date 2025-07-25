# /app/agents/process_reward_agent.py
# title: プロセス報酬AIエージェント
# role: 思考プロセスの各ステップを評価し、その正しさと有用性に対して報酬スコアを付与する。

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import JsonOutputParser
from typing import Any, Dict

from app.agents.base import AIAgent

class ProcessRewardAgent(AIAgent):
    """
    思考の各ステップを評価し、報酬を割り当てるAIエージェント。
    """
    def __init__(self, llm: Any, output_parser: JsonOutputParser, prompt_template: ChatPromptTemplate):
        self.llm = llm
        self.output_parser = output_parser
        self.prompt_template = prompt_template
        super().__init__()

    def build_chain(self) -> Runnable:
        """
        プロセス報酬エージェントのLangChainチェーンを構築します。
        """
        return self.prompt_template | self.llm | self.output_parser

    def invoke(self, input_data: Dict[str, Any] | str) -> Dict[str, Any]:
        """
        思考ステップを評価し、報酬スコアとフィードバックをJSON形式で返します。
        """
        if not isinstance(input_data, dict):
            raise TypeError("ProcessRewardAgent expects a dictionary as input.")
        
        if self._chain is None:
            raise RuntimeError("ProcessRewardAgent's chain is not initialized.")
        
        result: Dict[str, Any] = self._chain.invoke(input_data)
        return result
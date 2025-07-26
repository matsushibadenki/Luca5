# /app/pipelines/iterative_correction_pipeline.py
# title: 反復的修正パイプライン
# role: 「推測による修正」と「ステップバイステップ検証」を繰り返し、コードの品質を段階的に向上させる。

import logging
import time
from typing import Any, Dict

from app.pipelines.base import BasePipeline
from app.models import MasterAgentResponse, OrchestrationDecision
from app.agents.speculative_correction_agent import SpeculativeCorrectionAgent
from app.agents.step_by_step_verifier_agent import StepByStepVerifierAgent
from app.config import settings

logger = logging.getLogger(__name__)

class IterativeCorrectionPipeline(BasePipeline):
    """
    推測的修正とステップバイステップ検証を繰り返すパイプライン。
    """
    def __init__(
        self,
        speculative_correction_agent: SpeculativeCorrectionAgent,
        step_by_step_verifier_agent: StepByStepVerifierAgent,
    ):
        self.speculative_correction_agent = speculative_correction_agent
        self.step_by_step_verifier_agent = step_by_step_verifier_agent

    def run(self, query: str, orchestration_decision: OrchestrationDecision) -> MasterAgentResponse:
        """
        パイプラインを実行する。
        """
        start_time = time.time()
        logger.info("--- Iterative Correction Pipeline START ---")

        original_code = query
        current_code = query
        correction_history = ""
        max_iterations = settings.PIPELINE_SETTINGS.get("iterative_correction", {}).get("max_iterations", 3)

        for i in range(max_iterations):
            logger.info(f"--- 修正サイクル {i + 1}/{max_iterations} ---")

            correction_input = {"original_code": original_code, "current_code": current_code}
            speculative_fix = self.speculative_correction_agent.invoke(correction_input)
            
            verification_input = {"original_code": original_code, "proposed_fix": speculative_fix}
            verification_result = self.step_by_step_verifier_agent.invoke(verification_input)

            history_entry = f"--- Iteration {i+1} ---\nProposed Fix:\n{speculative_fix}\n\nVerification:\n{verification_result}\n\n"
            correction_history += history_entry

            if verification_result.get("is_correct", False):
                logger.info("検証エージェントが修正は正しいと判断しました。サイクルを終了します。")
                current_code = speculative_fix
                break
            else:
                logger.info("検証エージェントが問題点を指摘しました。次のサイクルで修正を試みます。")
                current_code = speculative_fix
        else:
            logger.warning("最大反復回数に達しました。")
        
        final_answer = current_code
        retrieved_info = correction_history

        logger.info(f"--- Iterative Correction Pipeline END ({(time.time() - start_time):.2f} s) ---")
        
        return MasterAgentResponse(
            final_answer=final_answer,
            self_criticism=f"{max_iterations}回の反復的修正と思考の検証を行いました。",
            potential_problems="検証エージェントが誤った判断をする可能性があります。最終的なコードは人間による確認が必要です。",
            retrieved_info=retrieved_info
        )
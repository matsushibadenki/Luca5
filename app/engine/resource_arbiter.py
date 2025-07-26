# /app/engine/resource_arbiter.py
# title: リソースアービター
# role: AIの認知エネルギーの状態に基づき、最終的な思考パイプライン（実行モード）を決定する。

from __future__ import annotations
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import OrchestrationDecision
    from app.meta_intelligence.cognitive_energy.manager import CognitiveEnergyManager

logger = logging.getLogger(__name__)

class ResourceArbiter:
    """
    認知リソースを管理し、パイプラインの選択を最終決定する仲裁者。
    """
    def __init__(self, energy_manager: "CognitiveEnergyManager"):
        self.energy_manager = energy_manager
        logger.info("ResourceArbiter initialized.")

    def arbitrate(self, decision: "OrchestrationDecision") -> "OrchestrationDecision":
        """
        現在の認知エネルギー状態に基づいて、オーケストレーションの決定を仲裁・調整する。
        """
        # CognitiveEnergyManagerの正しいメソッド名 `get_current_energy_level` を呼び出すように修正
        current_energy = self.energy_manager.get_current_energy_level()
        logger.info(f"Arbitrating decision. Current cognitive energy: {current_energy:.2f}")

        # Pydanticモデルの属性としてアクセスするように修正
        chosen_pipeline = decision.chosen_mode

        # エネルギー消費量が多いパイプライン
        high_energy_pipelines = ["tree_of_thoughts", "full", "self_discover"]

        # エネルギーが低い場合、高コストのパイプラインをよりシンプルなものに変更する
        if chosen_pipeline in high_energy_pipelines and current_energy < 40:
            logger.warning(
                f"Cognitive energy ({current_energy:.2f}) is low. "
                f"Overriding pipeline choice from '{chosen_pipeline}' to 'simple'."
            )
            # Pydanticモデルの属性を直接変更する
            decision.chosen_mode = "simple"
            decision.reasoning += " (Overridden by ResourceArbiter due to low cognitive energy)"
            decision.confidence_score = min(decision.confidence_score, 0.6)

        logger.info(f"Final pipeline decision after arbitration: {decision.chosen_mode}")
        return decision
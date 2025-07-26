# /physical_simulation/simulation_manager.py
# title: シミュレーションマネージャー
# role: 物理シミュレーションの実行、強化学習エージェントの訓練、結果の評価という一連のライフサイクルを管理する。

import logging
from typing import Dict, Any, Optional

import numpy as np
from physical_simulation.environments.block_stacking_env import BlockStackingEnv
from physical_simulation.results_analyzer import SimulationEvaluatorAgent
from physical_simulation.agents.base_agent import BaseRLAgent
from app.config import settings

logger = logging.getLogger(__name__)

class SimulationManager:
    """
    物理シミュレーションのライフサイクルを管理するオーケストレーター。
    """
    def __init__(
        self,
        evaluator_agent: SimulationEvaluatorAgent,
        rl_agent: BaseRLAgent,
        environment: BlockStackingEnv,
    ):
        self.evaluator_agent = evaluator_agent
        self.rl_agent = rl_agent
        self.environment = environment
        
        ppo_settings = settings.RL_AGENT_SETTINGS['ppo']
        self.max_ep_len = ppo_settings['max_ep_len']
        self.update_timestep = self.max_ep_len * ppo_settings['update_timestep_factor']

    def run_simulation_cycle(self) -> Optional[Dict[str, Any]]:
        """
        単一の完全なシミュレーション・学習サイクルを実行し、結果（洞察）を返す。
        """
        logger.info("--- 物理シミュレーション学習サイクル開始 (MuJoCo) ---")
        
        task_description = "5つのブロックを、崩れないようにできるだけ高く積み上げる。"
        timestep_counter = 0
        
        state, _ = self.environment.reset()
        current_ep_reward: float = 0.0
        simulation_log = []
        
        for t in range(1, int(self.max_ep_len) + 1):
            timestep_counter += 1
            
            action, _ = self.rl_agent.select_action(state)
            state, reward, terminated, truncated, info = self.environment.step(action)
            
            if hasattr(self.rl_agent, 'buffer'):
                self.rl_agent.buffer.rewards.append(reward)
                self.rl_agent.buffer.is_terminals.append(terminated)
            
            current_ep_reward += float(reward)

            if timestep_counter % self.update_timestep == 0:
                if hasattr(self.rl_agent, 'update'):
                    self.rl_agent.update()

            simulation_log.append({"step": t, "action": action.tolist(), "reward": reward, "info": info})
            if terminated or truncated:
                break
        
        final_state = info
        logger.info(f"シミュレーション完了。最終報酬: {current_ep_reward:.2f}, タワーの高さ: {final_state.get('tower_height', 0):.2f}")
        
        evaluation_input = {
            "task_description": task_description,
            "simulation_log": str(simulation_log)[:4000], # 長すぎるログを切り詰め
            "final_state": str(final_state)
        }
        
        try:
            structured_experience = self.evaluator_agent.invoke(evaluation_input)
            if structured_experience and "insights" in structured_experience:
                logger.info(f"統合された洞察: {structured_experience['insights']}")
                return structured_experience
            else:
                 logger.warning("シミュレーション結果から洞察が得られませんでした。")
                 return None
        except Exception as e:
            logger.error(f"シミュレーション結果の評価中にエラーが発生しました: {e}", exc_info=True)
            return None
        finally:
            self.environment.close()
            logger.info("--- 物理シミュレーション学習サイクル終了 ---")
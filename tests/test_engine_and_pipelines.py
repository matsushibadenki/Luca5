# tests/test_engine_and_pipelines.py
# title: エンジンとパイプラインのユニット/統合テスト
# role: アプリケーションのEngine層とSimplePipeline層のユニットテストと統合テスト

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from langchain_core.runnables.base import RunnableConfig
from langchain_core.callbacks.manager import CallbackManagerForChainRun, AsyncCallbackManagerForChainRun
from typing import Any, Dict, Callable, Awaitable, List

from app.engine.engine import MetaIntelligenceEngine
from app.pipelines.simple_pipeline import SimplePipeline
from app.pipelines.base import BasePipeline
from app.models import MasterAgentResponse, OrchestrationDecision

class MockLLM(Runnable):
    def __init__(self, response_content: str):
        self.response_content = response_content

    def invoke(self, input: Any, config: RunnableConfig | None = None, **kwargs: Any) -> Any:
        return self.response_content

    async def ainvoke(self, input: Any, config: RunnableConfig | None = None, **kwargs: Any) -> Any:
        return self.response_content

class MockLLMProvider:
    def get_llm_instance(self, model: str, **kwargs) -> MockLLM:
        return MockLLM(response_content="dummy llm instance response")

class MockResourceArbiter:
    def arbitrate(self, decision: OrchestrationDecision) -> OrchestrationDecision:
        if decision.chosen_mode not in ["simple", "full"]:
            decision.chosen_mode = "simple"
            decision.reasoning = (
                f"FALLBACK: Insufficient energy for original choice "
                f"'{decision.chosen_mode}'. Original reason: {decision.reasoning}"
            )
        return decision

class MockRetriever:
    def __init__(self, docs: list[Document]):
        self.docs = docs

    def invoke(self, query: str) -> list[Document]:
        return self.docs

class MockPromptManager:
    def get_prompt(self, name: str) -> ChatPromptTemplate:
        prompts = {
            "ROUTING_PROMPT": "Route query: {query}",
            "SIMPLE_MASTER_AGENT_PROMPT": "Answer based on: {query} and {retrieved_info}",
            "DIRECT_RESPONSE_PROMPT": "Direct answer: {query}"
        }
        return ChatPromptTemplate.from_template(prompts.get(name, f"Default prompt for {name}: {{query}}"))


class TestMetaIntelligenceEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_resource_arbiter = MockResourceArbiter()
        
        self.mock_simple_pipeline = MagicMock(spec=BasePipeline)
        self.mock_simple_pipeline.arun = AsyncMock(return_value=MasterAgentResponse(
            final_answer="Mocked Simple Pipeline Response for Engine Test",
            self_criticism="", potential_problems="", retrieved_info=""
        ))

        self.mock_full_pipeline = MagicMock(spec=BasePipeline)
        self.mock_full_pipeline.arun = AsyncMock(return_value=MasterAgentResponse(
            final_answer="Mocked Full Pipeline Response for Engine Test",
            self_criticism="", potential_problems="", retrieved_info=""
        ))

        self.pipelines = {
            "simple": self.mock_simple_pipeline,
            "full": self.mock_full_pipeline,
        }
        self.engine = MetaIntelligenceEngine(
            pipelines=self.pipelines,
            resource_arbiter=self.mock_resource_arbiter
        )

    async def test_meta_intelligence_engine_simple_mode_execution(self):
        query = "今日の天気は？"
        orchestration_decision = OrchestrationDecision(
            chosen_mode="simple",
            reasoning="weather_query",
            confidence_score=0.9,
            parameters={"reasoning_emphasis": "current_info"}
        )
        
        response = await self.engine.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "Mocked Simple Pipeline Response for Engine Test")
        self.mock_simple_pipeline.arun.assert_called_once_with(query, orchestration_decision)
        self.mock_full_pipeline.arun.assert_not_called()

    async def test_meta_intelligence_engine_full_mode_execution(self):
        query = "AIの意識とは何か、哲学的に論じなさい。"
        orchestration_decision = OrchestrationDecision(
            chosen_mode="full",
            reasoning="philosophical_query",
            confidence_score=0.9,
            parameters={"reasoning_emphasis": "conceptual"}
        )
        
        response = await self.engine.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "Mocked Full Pipeline Response for Engine Test")
        self.mock_full_pipeline.arun.assert_called_once_with(query, orchestration_decision)
        self.mock_simple_pipeline.arun.assert_not_called()

    async def test_meta_intelligence_engine_invalid_mode_fallback(self):
        query = "何でもいいよ"
        orchestration_decision = OrchestrationDecision(
            chosen_mode="invalid_mode",
            reasoning="testing_fallback",
            confidence_score=0.8,
            parameters={"reasoning_emphasis": "none"}
        )
        
        response = await self.engine.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "Mocked Simple Pipeline Response for Engine Test")
        
        # Check that the decision was modified by the arbiter
        self.mock_simple_pipeline.arun.assert_called_once()
        call_args, _ = self.mock_simple_pipeline.arun.call_args
        self.assertEqual(call_args[0], query)
        modified_decision = call_args[1]
        self.assertEqual(modified_decision.chosen_mode, "simple")
        self.assertIn("FALLBACK", modified_decision.reasoning)

        self.mock_full_pipeline.arun.assert_not_called()

class TestSimplePipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_prompt_manager = MockPromptManager()
        self.mock_retriever = MagicMock(spec=MockRetriever)
        self.mock_retriever.invoke.return_value = [Document(page_content="retrieved info for rag")]

        self.mock_llm_router = AsyncMock(return_value={"route": "DIRECT"})
        self.mock_llm_direct = AsyncMock(return_value="Mocked Direct response")
        self.mock_llm_rag = AsyncMock(return_value="Mocked RAG response")

        # Reconstruct the pipeline with mocks
        self.simple_pipeline = SimplePipeline(
            llm=MagicMock(), # This won't be used directly
            output_parser=StrOutputParser(),
            retriever=self.mock_retriever,
            prompt_manager=self.mock_prompt_manager
        )
        # Override chains with mocks
        self.simple_pipeline.router_chain = MagicMock(spec=Runnable)
        self.simple_pipeline.router_chain.ainvoke = self.mock_llm_router
        self.simple_pipeline.direct_chain = MagicMock(spec=Runnable)
        self.simple_pipeline.direct_chain.ainvoke = self.mock_llm_direct
        self.simple_pipeline.rag_chain = MagicMock(spec=Runnable)
        self.simple_pipeline.rag_chain.ainvoke = self.mock_llm_rag

    async def test_simple_pipeline_direct_route(self):
        self.mock_llm_router.return_value = {"route": "DIRECT"}
        self.mock_llm_direct.return_value = "Direct answer for hello"
        
        query = "こんにちは"
        orchestration_decision = OrchestrationDecision(chosen_mode="simple", reasoning="greeting", confidence_score=0.9)
        
        response = await self.simple_pipeline.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "Direct answer for hello")
        self.assertEqual(response.retrieved_info, "")
        self.mock_retriever.invoke.assert_not_called()
        self.mock_llm_router.assert_called_once()
        self.mock_llm_direct.assert_called_once()
        self.mock_llm_rag.assert_not_called()

    async def test_simple_pipeline_rag_route_success(self):
        self.mock_llm_router.return_value = {"route": "RAG"}
        self.mock_llm_rag.return_value = "RAG answer about fish"
        
        query = "さんまについて教えてください"
        orchestration_decision = OrchestrationDecision(chosen_mode="simple", reasoning="info_query", confidence_score=0.9)
        
        response = await self.simple_pipeline.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "RAG answer about fish")
        self.assertEqual(response.retrieved_info, "retrieved info for rag")
        self.mock_retriever.invoke.assert_called_once_with(query)
        self.mock_llm_router.assert_called_once()
        self.mock_llm_rag.assert_called_once()
        self.mock_llm_direct.assert_not_called()

    async def test_simple_pipeline_rag_route_no_retrieval_fallback(self):
        self.mock_llm_router.return_value = {"route": "RAG"}
        self.mock_retriever.invoke.return_value = []
        self.mock_llm_direct.return_value = "Direct fallback answer"
        
        query = "存在しないトピックについて"
        orchestration_decision = OrchestrationDecision(chosen_mode="simple", reasoning="info_query_no_data", confidence_score=0.9)
        
        response = await self.simple_pipeline.arun(query, orchestration_decision)

        self.assertEqual(response.final_answer, "Direct fallback answer")
        self.assertEqual(response.retrieved_info, "")
        self.mock_retriever.invoke.assert_called_once_with(query)
        self.mock_llm_router.assert_called_once()
        self.mock_llm_direct.assert_called_once()
        self.mock_llm_rag.assert_not_called()
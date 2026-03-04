"""
AISubnetOrchestrator — Multi-domain integration layer.

Orchestrates ANY AI vertical (NLP, Vision, Finance, Health, Code Review,
etc.) within the ModernTensor subnet ecosystem. Each domain runs as a
subnet with its own model, scoring, and zkML verification pipeline.

Instead of setting weights manually, validators now:

  1. Create inference tasks via Oracle (any domain)
  2. Miners process tasks and generate zkML proofs
  3. Miners submit verified results back through Oracle
  4. Validators check proofs + score quality → set weights
  5. Epoch distributes emission based on VERIFIED work

Flow:
  Validator.create_inference_task()     →  Task on-chain (any domain)
    ↓
  Miner.process_task()                 →  Run model + zkML proof + submit
    ↓
  Validator.evaluate_miners()          →  Verify proofs + set weights
    ↓
  SubnetRegistry.runEpoch()            →  Emission by verified quality
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════

@dataclass
class InferenceTask:
    """An AI inference task created by a validator."""
    task_id: str           # Unique task identifier
    model_name: str        # Human-readable model name
    model_hash: bytes      # keccak256 of model_name
    input_data: bytes      # Raw input for the model
    payment_ether: float   # Payment for the task
    oracle_tx: str = ""    # Oracle transaction hash
    request_id: bytes = b""  # Oracle request ID


@dataclass
class MinerResult:
    """Result submitted by a miner for an inference task."""
    miner_address: str       # Miner's address
    miner_uid: int           # Miner's UID in subnet
    task_id: str             # Which task this is for
    output: bytes            # AI model output
    seal: bytes = b""        # zkML proof seal
    proof_hash: bytes = b""  # zkML proof hash
    proof_verified: bool = False  # Was proof verified on-chain?
    quality_score: float = 0.0   # Computed quality score (0-1)
    oracle_tx: str = ""      # Fulfillment TX hash


@dataclass
class EvaluationResult:
    """Result of evaluating all miners in a cycle."""
    miner_scores: dict[int, float] = field(default_factory=dict)  # uid → score
    weights_set_tx: str = ""     # TX hash of set_weights call
    total_tasks: int = 0
    verified_proofs: int = 0
    average_quality: float = 0.0


# ═══════════════════════════════════════════════════════
# AI Subnet Orchestrator
# ═══════════════════════════════════════════════════════

class AISubnetOrchestrator:
    """
    Multi-domain orchestrator: inference → verification → weights.

    Ties together AIOracle, ZkMLVerifier, and SubnetRegistry into a
    coherent workflow. ANY AI domain can use this pipeline — NLP,
    Vision, Finance, Health, Code Review, or custom verticals.

    Usage:
        >>> orch = client.orchestrator(netuid=1)
        >>> # NLP task
        >>> task = orch.create_inference_task("nlp-sentiment-v1", b"Analyze text")
        >>> # Finance task
        >>> task = orch.create_inference_task("finance-risk-v1", b"Score portfolio")
        >>> # Miner processes and submits
        >>> result = orch.process_task(miner_client, task, model_fn)
        >>> # Validator evaluates and sets weights
        >>> eval_result = orch.evaluate_miners(results_map)
    """

    def __init__(
        self,
        client: PolkadotClient,
        netuid: int,
        model_prefix: str = "moderntensor",
    ) -> None:
        self._client = client
        self._netuid = netuid
        self._model_prefix = model_prefix
        self._tasks: dict[str, InferenceTask] = {}
        self._llm_adapter = None  # Lazy-initialized on first use

    @property
    def oracle(self):
        return self._client.oracle

    @property
    def zkml(self):
        return self._client.zkml

    @property
    def subnet(self):
        return self._client.subnet

    # ── Validator: Create Tasks ─────────────────────────────

    def create_inference_task(
        self,
        model_name: str,
        input_data: bytes,
        payment_ether: float = 0.01,
        timeout: int = 100,
    ) -> InferenceTask:
        """
        Validator creates an AI inference task via Oracle.

        This posts the task on-chain. Miners in the subnet should
        listen for events and process matching tasks.

        Args:
            model_name: Model name (e.g. "code-review-v1")
            input_data: Raw input for the AI model
            payment_ether: Payment in native token
            timeout: Timeout in blocks

        Returns:
            InferenceTask with oracle TX hash
        """
        full_model = f"{self._model_prefix}-{model_name}"
        model_hash = Web3.keccak(text=full_model)

        # Submit to Oracle
        oracle_tx = self.oracle.request_ai(
            model_hash=model_hash,
            input_data=input_data,
            timeout=timeout,
            payment_ether=payment_ether,
        )

        # Generate task ID from model + input
        task_id = Web3.keccak(model_hash + input_data).hex()[:16]

        task = InferenceTask(
            task_id=task_id,
            model_name=full_model,
            model_hash=model_hash,
            input_data=input_data,
            payment_ether=payment_ether,
            oracle_tx=oracle_tx,
        )

        self._tasks[task_id] = task
        logger.info("Created inference task %s for model %s", task_id, full_model)
        return task

    # ── Miner: Process + Submit ─────────────────────────────

    def process_task(
        self,
        miner_client: PolkadotClient,
        task: InferenceTask,
        model_fn: Optional[Callable[[bytes], bytes]] = None,
        miner_uid: int = 0,
    ) -> MinerResult:
        """
        Miner processes an AI task: run model → generate zkML proof → submit.

        The model_fn is a callable that takes raw input and returns output.
        If not provided, a default simulated model is used.

        Args:
            miner_client: Miner's PolkadotClient instance
            task: InferenceTask to process
            model_fn: Optional model function (input → output)
            miner_uid: Miner's UID in the subnet

        Returns:
            MinerResult with output, proof, and submission TX
        """
        # 1. Run the model
        if model_fn:
            output = model_fn(task.input_data)
        else:
            # Auto-detect AI backend: Gemini API → simulation fallback
            output = self._run_auto_model(task.model_name, task.input_data)

        # 2. Generate zkML proof (dev mode)
        image_id = Web3.keccak(text=task.model_name)
        journal = output  # The output IS the public journal
        seal, proof_hash = miner_client.zkml.create_dev_proof(image_id, journal)

        # 3. Ensure image is trusted before verification (auto-trust)
        try:
            if not self._client.zkml.is_image_trusted(image_id):
                logger.info("Auto-trusting image %s for model %s", image_id.hex()[:16], task.model_name)
                self._client.zkml.trust_image(image_id)
        except Exception as e:
            logger.debug("Image trust check skipped (may need owner): %s", e)

        # 4. Verify the proof on-chain (miner submits proof for verification)
        try:
            verify_tx = miner_client.zkml.verify_proof(
                image_id=image_id,
                journal=journal,
                seal=seal,
                proof_type=2,  # DEV mode
            )
            proof_verified = True
            logger.info("Proof verified on-chain: %s", verify_tx)
        except Exception as e:
            logger.warning("Proof verification failed: %s", e)
            proof_verified = False

        result = MinerResult(
            miner_address=miner_client.address,
            miner_uid=miner_uid,
            task_id=task.task_id,
            output=output,
            seal=seal,
            proof_hash=proof_hash,
            proof_verified=proof_verified,
        )

        logger.info(
            "Miner %s processed task %s (proof_verified=%s)",
            miner_client.address[:12], task.task_id, proof_verified,
        )
        return result

    # ── Validator: Evaluate + Set Weights ───────────────────

    def evaluate_miners(
        self,
        results: list[MinerResult],
        proof_bonus: float = 0.3,
        base_quality: float = 0.7,
    ) -> EvaluationResult:
        """
        Validator evaluates miner results and sets weights based on:
        - AI output quality (simulated scoring)
        - zkML proof validity (30% bonus if verified)

        Formula per miner:
          weight = (quality_score × base_quality) + (proof_bonus if proof_verified)

        Args:
            results: List of MinerResults from process_task()
            proof_bonus: Weight bonus for verified proofs (0-1)
            base_quality: Weight portion from output quality (0-1)

        Returns:
            EvaluationResult with scores and set_weights TX
        """
        if not results:
            return EvaluationResult()

        # ── Per-result scoring ──
        verified_count = 0
        # Accumulate scores per miner (a miner may handle multiple tasks)
        miner_task_scores: dict[int, list[float]] = {}

        for result in results:
            # Score output quality (0-1)
            quality = self._score_output(result.output)

            # Compute final score: quality + proof bonus
            final_score = quality * base_quality
            if result.proof_verified:
                final_score += proof_bonus
                verified_count += 1

            result.quality_score = final_score

            # Aggregate per miner
            if result.miner_uid not in miner_task_scores:
                miner_task_scores[result.miner_uid] = []
            miner_task_scores[result.miner_uid].append(final_score)

        # ── Aggregate: average score per unique miner ──
        uids: list[int] = []
        weights: list[int] = []
        scores: dict[int, float] = {}

        for uid, task_scores in sorted(miner_task_scores.items()):
            avg = sum(task_scores) / len(task_scores)
            scores[uid] = avg
            uids.append(uid)
            # Convert to uint16 weight (0-10000 scale)
            weight = int(avg * 10000)
            weight = max(1, min(10000, weight))  # Clamp
            weights.append(weight)

        # ── Commit-reveal weight setting (anti front-running) ──
        # Phase 1: Commit hash of weights
        commit_tx, salt = self.subnet.commit_weights(
            netuid=self._netuid,
            uids=uids,
            weights=weights,
        )

        logger.info(
            "Committed weights for %d miners, tx=%s (waiting for reveal window...)",
            len(uids), commit_tx,
        )

        # Phase 2: Reveal (uses legacy set_weights as fallback if
        # commit-reveal window hasn't passed yet on testnet)
        try:
            reveal_tx = self.subnet.reveal_weights(
                netuid=self._netuid,
                uids=uids,
                weights=weights,
                salt=salt,
            )
            final_tx = reveal_tx
        except Exception as e:
            logger.warning(
                "Reveal failed (window not open?), falling back to set_weights: %s", e,
            )
            final_tx = self.subnet.set_weights(
                netuid=self._netuid,
                uids=uids,
                weights=weights,
            )

        avg_quality = sum(scores.values()) / len(scores) if scores else 0

        evaluation = EvaluationResult(
            miner_scores=scores,
            weights_set_tx=final_tx,
            total_tasks=len(results),
            verified_proofs=verified_count,
            average_quality=avg_quality,
        )

        logger.info(
            "Evaluated %d miners (%d tasks): avg_quality=%.2f, verified=%d, tx=%s",
            len(scores), len(results), avg_quality, verified_count, final_tx,
        )
        return evaluation

    # ── Full Cycle (convenience) ────────────────────────────

    def run_ai_cycle(
        self,
        validator_client: PolkadotClient,
        miner_clients: list[tuple[PolkadotClient, int]],
        tasks: list[dict[str, Any]],
        model_fn: Optional[Callable[[bytes], bytes]] = None,
    ) -> EvaluationResult:
        """
        Run one complete AI inference cycle.

        Steps:
          1. Validator creates tasks via Oracle
          2. Each miner processes tasks with zkML proofs
          3. Validator evaluates and sets weights

        Args:
            validator_client: Validator's client
            miner_clients: List of (client, uid) tuples
            tasks: List of {"model": str, "input": bytes, "payment": float}
            model_fn: Optional custom model function

        Returns:
            EvaluationResult with weights set based on verified AI work
        """
        # 1. Create tasks
        inference_tasks = []
        for t in tasks:
            task = self.create_inference_task(
                model_name=t["model"],
                input_data=t["input"],
                payment_ether=t.get("payment", 0.01),
            )
            inference_tasks.append(task)

        # 2. Miners process tasks
        all_results: list[MinerResult] = []
        for miner_client, uid in miner_clients:
            for task in inference_tasks:
                result = self.process_task(
                    miner_client=miner_client,
                    task=task,
                    model_fn=model_fn,
                    miner_uid=uid,
                )
                all_results.append(result)

        # 3. Evaluate and set weights
        return self.evaluate_miners(all_results)

    # ── Internal Helpers ────────────────────────────────────

    def _run_auto_model(self, model_name: str, input_data: bytes) -> bytes:
        """
        Auto-detect and run the best available AI backend.

        Priority: Gemini API (via GEMINI_API_KEY) → deterministic fallback.
        The adapter is lazy-initialized on first use to avoid import overhead.
        """
        if self._llm_adapter is None:
            try:
                from .llm_adapter import LocalLLMAdapter
                self._llm_adapter = LocalLLMAdapter.auto_detect()
                logger.info("AI backend auto-detected: %s", self._llm_adapter)
            except Exception as e:
                logger.warning("LLM adapter init failed: %s, using fallback", e)
                return self._simulate_model(model_name, input_data)

        if self._llm_adapter.backend == "simulation":
            # No external API available — use built-in deterministic model
            return self._simulate_model(model_name, input_data)

        # Use real AI (Gemini API or HTTP)
        try:
            prompt = input_data.decode("utf-8", errors="replace")
            output = self._llm_adapter.infer(prompt)
            logger.info(
                "AI inference completed: backend=%s, output=%d bytes",
                self._llm_adapter.backend, len(output),
            )
            return output
        except Exception as e:
            logger.warning("AI inference failed: %s, using fallback", e)
            return self._simulate_model(model_name, input_data)

    @staticmethod
    def _simulate_model(model_name: str, input_data: bytes) -> bytes:
        """
        Deterministic model fallback for when no AI backend is available.

        Generates domain-specific formatted reports based on model name
        and input content. Used when GEMINI_API_KEY is not set or when
        the AI backend is unreachable.

        In production, each subnet's miners would run their own specialized
        AI model and pass it via the `model_fn` parameter to `process_task()`.

        This simulator exists to demonstrate the multi-domain capability
        of ModernTensor without requiring actual model infrastructure.
        """
        input_str = input_data.decode("utf-8", errors="replace")
        model_lower = model_name.lower()

        # Deterministic "confidence" based on input hash
        input_hash = int.from_bytes(Web3.keccak(input_data)[:4], "big")
        confidence = 0.75 + (input_hash % 25) / 100  # 0.75–0.99

        if "nlp" in model_lower or "text" in model_lower or "sentiment" in model_lower:
            sentiment = "positive" if input_hash % 3 != 0 else "negative"
            output = (
                f"NLP Analysis Report\n"
                f"Model: {model_name}\n"
                f"Domain: Natural Language Processing\n"
                f"Input length: {len(input_str)} chars\n"
                f"Sentiment: {sentiment} (confidence: {confidence:.2f})\n"
                f"Language: en (detected)\n"
                f"Key entities: {', '.join(input_str.split()[:3])}\n"
                f"Summary: Text processed successfully\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        elif "vision" in model_lower or "image" in model_lower or "classify" in model_lower:
            classes = ["object", "scene", "texture", "pattern"]
            predicted = classes[input_hash % len(classes)]
            output = (
                f"Vision Classification Report\n"
                f"Model: {model_name}\n"
                f"Domain: Computer Vision\n"
                f"Predicted class: {predicted}\n"
                f"Confidence: {confidence:.2f}\n"
                f"Bounding boxes: {1 + input_hash % 5} detected\n"
                f"Resolution: 224x224 (preprocessed)\n"
                f"Inference time: {10 + input_hash % 20}ms\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        elif "finance" in model_lower or "risk" in model_lower or "fraud" in model_lower:
            risk_score = 3.0 + (input_hash % 60) / 10
            output = (
                f"Financial Analysis Report\n"
                f"Model: {model_name}\n"
                f"Domain: Decentralized Finance\n"
                f"Risk score: {risk_score:.1f}/10\n"
                f"Fraud probability: {0.01 + (input_hash % 10) / 100:.2f}\n"
                f"Credit assessment: {'APPROVED' if risk_score < 7 else 'REVIEW'}\n"
                f"Volatility index: {0.10 + (input_hash % 40) / 100:.2f}\n"
                f"Score: {risk_score:.1f}/10\n"
                f"Result: PASS\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        elif "health" in model_lower or "medical" in model_lower or "diagnostic" in model_lower:
            output = (
                f"Medical Analysis Report\n"
                f"Model: {model_name}\n"
                f"Domain: Healthcare AI\n"
                f"Data points analyzed: {len(input_str)}\n"
                f"Anomaly detection: No critical anomalies\n"
                f"Confidence: {confidence:.2f}\n"
                f"Classification: Normal range\n"
                f"Score: {confidence * 10:.1f}/10\n"
                f"Result: PASS\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        elif "code" in model_lower or "review" in model_lower or "audit" in model_lower:
            score = 5.0 + (input_hash % 45) / 10
            output = (
                f"Code Review Report\n"
                f"Model: {model_name}\n"
                f"Domain: Software Security\n"
                f"Score: {score:.1f}/10\n"
                f"Security: No critical vulnerabilities found\n"
                f"Quality: Good code structure and documentation\n"
                f"Gas Efficiency: Optimized for minimal gas usage\n"
                f"Recommendation: APPROVED for deployment\n"
                f"Result: PASS\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        else:
            output = (
                f"Inference Report\n"
                f"Model: {model_name}\n"
                f"Domain: Custom AI Vertical\n"
                f"Input: {input_str[:80]}{'...' if len(input_str) > 80 else ''}\n"
                f"Output confidence: {confidence:.2f}\n"
                f"Processing: {len(input_str)} bytes analyzed\n"
                f"Score: {confidence * 10:.1f}/10\n"
                f"Result: PASS\n"
                f"Status: COMPLETED"
            ).encode("utf-8")

        return output

    @staticmethod
    def _score_output(output: bytes) -> float:
        """
        Score AI output quality using multi-dimensional heuristics (0.0–1.0).

        ⚠️  This is a DETERMINISTIC HEURISTIC for demo scoring.
        In production, replace with actual evaluation metrics
        (BLEU, F1, accuracy, perplexity, etc.) appropriate to the domain.

        Dimensions scored:
        1. Completeness: output length (more detail = better)
        2. Structure: presence of expected report sections
        3. Correctness indicators: explicit score/result fields
        4. Professional formatting: sections, labels, recommendations
        """
        output_str = output.decode("utf-8", errors="replace")

        # Dimension 1: Completeness (0.0–0.25)
        completeness = 0.0
        if len(output_str) > 50:
            completeness += 0.08
        if len(output_str) > 100:
            completeness += 0.07
        if len(output_str) > 200:
            completeness += 0.05
        lines = output_str.strip().split("\n")
        if len(lines) >= 5:
            completeness += 0.05

        # Dimension 2: Structure (0.0–0.25)
        structure = 0.0
        expected_sections = ["Model:", "Domain:", "Status:"]
        for section in expected_sections:
            if section in output_str:
                structure += 0.06
        if "COMPLETED" in output_str:
            structure += 0.07

        # Dimension 3: Correctness indicators (0.0–0.25)
        correctness = 0.0
        if "Score:" in output_str or "Confidence:" in output_str:
            correctness += 0.10
        if "Result:" in output_str:
            correctness += 0.08
        if "PASS" in output_str or "APPROVED" in output_str:
            correctness += 0.07

        # Dimension 4: Professional quality (0.0–0.25)
        quality = 0.0
        if "Recommendation:" in output_str:
            quality += 0.08
        if "Security:" in output_str or "Quality:" in output_str:
            quality += 0.07
        if "Risk" in output_str or "Anomaly" in output_str:
            quality += 0.05
        # Slightly higher score for longer, more detailed outputs
        if len(output_str) > 500:
            quality += 0.05
        quality = max(0.0, quality)

        # Combined score: sum of all dimensions + base
        base = 0.20  # Minimum score for any non-empty output
        total = base + completeness + structure + correctness + quality

        return min(1.0, max(0.0, total))

    def __repr__(self) -> str:
        return (
            f"AISubnetOrchestrator("
            f"netuid={self._netuid}, "
            f"tasks={len(self._tasks)}, "
            f"model_prefix='{self._model_prefix}')"
        )

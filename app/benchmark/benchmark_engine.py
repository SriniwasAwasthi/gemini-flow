"""
AI Performance & Benchmark Engine for Gemini Flow.
Tracks system-wide latency (P50, P95, Avg), success/failure rates, model utilization,
and provides an automated 6-model benchmark suite matching Gemini_Flow_AI_Models_Guide.md.
"""
import os
import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable

import requests
from app.config import APP_DIR

logger = logging.getLogger("GeminiFlow.Benchmark")

METRICS_FILE = os.path.join(str(APP_DIR), "metrics.json")


@dataclass
class BenchmarkTestCase:
    id: str
    category: str
    description: str
    system_instruction: str
    input_text: str
    expected_keywords: List[str]


BENCHMARK_TEST_SUITE: List[BenchmarkTestCase] = [
    BenchmarkTestCase(
        id="casual_speech",
        category="Casual / Daily Speech",
        description="Daily conversational speech transcription and light punctuation.",
        system_instruction="Transcribe the spoken audio into clear, clean, and grammatically accurate text. Output ONLY the text.",
        input_text="hey how are you doing today hope your weekend was good and we can catch up later",
        expected_keywords=["weekend", "catch up", "today"]
    ),
    BenchmarkTestCase(
        id="tech_architecture",
        category="Technical & Architecture",
        description="High-density software architecture, microservices, and distributed terminology.",
        system_instruction="Format using accurate software architecture and engineering terminology. Output ONLY the text.",
        input_text="we need to deploy kubernetes ingress with grpc load balancing kafka event streaming and postgres read replicas",
        expected_keywords=["kubernetes", "grpc", "kafka", "postgres"]
    ),
    BenchmarkTestCase(
        id="names_phonetics",
        category="Global Names & Phonetics",
        description="Multi-cultural proper nouns, international founder names, and brand phonetics.",
        system_instruction="Ensure all proper nouns and international names are spelled with exact phonetic fidelity. Output ONLY the text.",
        input_text="dr priya subramaniam met with alexander vanderbilt and guillaume lefebvre at the symposium",
        expected_keywords=["priya", "alexander", "guillaume"]
    ),
    BenchmarkTestCase(
        id="numbers_code",
        category="Numbers, Symbols & Code",
        description="Programming syntax, variable casing, ports, IPs, and mathematical equations.",
        system_instruction="Format identifiers in camelCase or snake_case and numbers/ports accurately. Output ONLY the text.",
        input_text="set max retries to three and connect port 8080 on 127 0 0 1 with timeout equal to 15 seconds",
        expected_keywords=["8080", "127.0.0.1", "15"]
    ),
    BenchmarkTestCase(
        id="executive_rewrite",
        category="Executive Professional",
        description="Rewriting informal thoughts into high-stakes executive correspondence.",
        system_instruction="Rewrite in an articulate, authoritative, executive professional tone. Output ONLY the text.",
        input_text="hey team we messed up the deadline but were fixing it right now so dont worry too much",
        expected_keywords=["deadline", "remedying", "schedule", "progress", "mitigat"]
    ),
    BenchmarkTestCase(
        id="long_form_reasoning",
        category="Long-Form Reasoning",
        description="Multi-faceted trade-off analysis and structured synthesis.",
        system_instruction="Provide a structured architectural trade-off analysis with pros, cons, and recommendations. Output ONLY the analysis.",
        input_text="compare monolith versus microservices for an early stage startup with three engineers",
        expected_keywords=["monolith", "microservices", "trade", "complexity", "team"]
    )
]


@dataclass
class BenchmarkResult:
    model_name: str
    test_id: str
    category: str
    latency_seconds: float
    success: bool
    output_text: str
    accuracy_score: float  # 0 to 100
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsTracker:
    """Tracks live operation performance, latencies, model distribution, and fallbacks."""

    def __init__(self, metrics_file: str = METRICS_FILE):
        self.metrics_file = metrics_file
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.latencies: List[float] = []
        self.model_usage: Dict[str, int] = {}
        self.intent_usage: Dict[str, int] = {}
        self.app_usage: Dict[str, int] = {}
        self.total_words = 0
        self.fallbacks_triggered = 0
        self.load_metrics()

    def load_metrics(self):
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_requests = data.get("total_requests", 0)
                    self.successful_requests = data.get("successful_requests", 0)
                    self.failed_requests = data.get("failed_requests", 0)
                    self.latencies = data.get("latencies", [])[-1000:]
                    self.model_usage = data.get("model_usage", {})
                    self.intent_usage = data.get("intent_usage", {})
                    self.app_usage = data.get("app_usage", {})
                    self.total_words = data.get("total_words", 0)
                    self.fallbacks_triggered = data.get("fallbacks_triggered", 0)
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")

    def save_metrics(self):
        try:
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            payload = {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "latencies": self.latencies[-1000:],
                "model_usage": self.model_usage,
                "intent_usage": self.intent_usage,
                "app_usage": self.app_usage,
                "total_words": self.total_words,
                "fallbacks_triggered": self.fallbacks_triggered,
                "last_updated": time.time()
            }
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

    def record_event(
        self,
        model: str,
        latency: float,
        success: bool,
        words_count: int = 0,
        intent: str = "DICTATE",
        app_name: str = "",
        fallback: bool = False
    ):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        if latency > 0:
            self.latencies.append(round(latency, 3))
            if len(self.latencies) > 1000:
                self.latencies.pop(0)

        self.model_usage[model] = self.model_usage.get(model, 0) + 1
        self.intent_usage[intent] = self.intent_usage.get(intent, 0) + 1

        if app_name:
            self.app_usage[app_name] = self.app_usage.get(app_name, 0) + 1

        self.total_words += words_count
        if fallback:
            self.fallbacks_triggered += 1

        # Periodic save (every 3 events or on failure)
        if self.total_requests % 3 == 0 or not success:
            self.save_metrics()

    def get_summary(self) -> Dict[str, Any]:
        success_pct = (
            (self.successful_requests / self.total_requests * 100)
            if self.total_requests > 0 else 100.0
        )

        sorted_latencies = sorted(self.latencies)
        p50 = 0.0
        p95 = 0.0
        avg_lat = 0.0

        if sorted_latencies:
            n = len(sorted_latencies)
            p50 = sorted_latencies[int(n * 0.50)]
            p95 = sorted_latencies[min(int(n * 0.95), n - 1)]
            avg_lat = sum(sorted_latencies) / n

        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_pct": round(success_pct, 1),
            "success_rate": round(success_pct, 1),
            "p50_latency_sec": round(p50, 2),
            "p50_latency": round(p50, 2),
            "p95_latency_sec": round(p95, 2),
            "p95_latency": round(p95, 2),
            "avg_latency_sec": round(avg_lat, 2),
            "avg_latency": round(avg_lat, 2),
            "total_words": self.total_words,
            "fallbacks_triggered": self.fallbacks_triggered,
            "model_usage": self.model_usage,
            "intent_usage": self.intent_usage,
            "app_usage": self.app_usage
        }

    def clear_metrics(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.latencies = []
        self.model_usage = {}
        self.intent_usage = {}
        self.app_usage = {}
        self.total_words = 0
        self.fallbacks_triggered = 0
        self.save_metrics()


class BenchmarkEngine:
    """Executes standardized test matrices across Gemini models."""

    @staticmethod
    def run_single_test(
        model: str,
        test_case: BenchmarkTestCase,
        api_key: str,
        session: Optional[requests.Session] = None
    ) -> BenchmarkResult:
        if not api_key:
            return BenchmarkResult(
                model_name=model,
                test_id=test_case.id,
                category=test_case.category,
                latency_seconds=0.0,
                success=False,
                output_text="",
                accuracy_score=0.0,
                error="Missing Gemini API Key"
            )

        http = session or requests.Session()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{test_case.system_instruction}\n\nINPUT:\n{test_case.input_text}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 600
            }
        }

        start_t = time.time()
        try:
            resp = http.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=12)
            latency = time.time() - start_t

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
                out_text = "".join([p.get("text", "") for p in parts if "text" in p]).strip()

                # Score quality based on matching expected keywords and length
                score = 60.0  # Base for valid response
                lower_out = out_text.lower()
                matched_kw = sum(1 for kw in test_case.expected_keywords if kw.lower() in lower_out)
                if test_case.expected_keywords:
                    score += 40.0 * (matched_kw / len(test_case.expected_keywords))

                return BenchmarkResult(
                    model_name=model,
                    test_id=test_case.id,
                    category=test_case.category,
                    latency_seconds=round(latency, 2),
                    success=True,
                    output_text=out_text,
                    accuracy_score=round(score, 1)
                )
            else:
                err = resp.text
                return BenchmarkResult(
                    model_name=model,
                    test_id=test_case.id,
                    category=test_case.category,
                    latency_seconds=round(latency, 2),
                    success=False,
                    output_text="",
                    accuracy_score=0.0,
                    error=f"API Error {resp.status_code}: {err[:120]}"
                )
        except Exception as e:
            return BenchmarkResult(
                model_name=model,
                test_id=test_case.id,
                category=test_case.category,
                latency_seconds=round(time.time() - start_t, 2),
                success=False,
                output_text="",
                accuracy_score=0.0,
                error=str(e)
            )

    @classmethod
    def run_model_suite(
        cls,
        model: str,
        api_key: str,
        progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> List[BenchmarkResult]:
        session = requests.Session()
        results = []
        total = len(BENCHMARK_TEST_SUITE)

        for i, test_case in enumerate(BENCHMARK_TEST_SUITE):
            if progress_cb:
                progress_cb(i + 1, total, f"Running {model} on {test_case.category}...")
            res = cls.run_single_test(model, test_case, api_key, session=session)
            results.append(res)
            time.sleep(0.2)

        return results

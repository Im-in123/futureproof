"""Track cost per receipt. Every model call tracked with latency."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ModelCall:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_s: float = 0.0


@dataclass
class CostTracker:
    PRICES = {
        "lightning": (0.05, 0.20),
        "super":     (0.30, 0.90),
    }
    TAVILY_COST_PER_CALL = 0.016

    model_calls: list[ModelCall] = field(default_factory=list)
    tavily_calls: int = 0
    latency_seconds: float = 0.0

    def record_model(self, model: str, prompt_tokens: int,
                     completion_tokens: int, latency_s: float = 0.0) -> None:
        key = "super" if "super" in model.lower() else "lightning"
        in_p, out_p = self.PRICES[key]
        cost = (prompt_tokens * in_p + completion_tokens * out_p) / 1_000_000
        # Construct with latency directly — no post-mutation
        self.model_calls.append(ModelCall(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_s=latency_s,
        ))

    def record_tavily(self, n: int = 1) -> None:
        self.tavily_calls += n

    def summary(self) -> dict:
        llm_cost = sum(c.cost_usd for c in self.model_calls)
        tavily_cost = self.tavily_calls * self.TAVILY_COST_PER_CALL
        return {
            "model_calls": [
                {
                    "model": c.model,
                    "in": c.prompt_tokens,
                    "out": c.completion_tokens,
                    "cost_usd": round(c.cost_usd, 6),
                    "latency_s": round(c.latency_s, 2),
                }
                for c in self.model_calls
            ],
            "tavily_calls": self.tavily_calls,
            "llm_cost_usd": round(llm_cost, 6),
            "tavily_cost_usd": round(tavily_cost, 6),
            "total_cost_usd": round(llm_cost + tavily_cost, 6),
            "latency_seconds": round(self.latency_seconds, 2),
            "pricing_note": "Nebius Token Factory list prices; NVIDIA free tier used for this run",
        }

"""
Cost-Awareness, Dynamic Pricing & Productivity Analytics Engine for Gemini Flow.
Tracks daily, weekly, and all-time API consumption, calculates estimated USD costs,
computes total spoken words against gamified publication milestones (Book, Chapter, Magazine, Essay),
and analyzes net time saved versus manual typing.
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("GeminiFlow.CostAwareness")

# Google Gemini Official API Pricing Matrix (USD)
# Units: Tokens per 1,000,000, Audio input in seconds (1 min = ~150-200 words = ~9,000 audio tokens)
MODEL_PRICING: Dict[str, Dict[str, Any]] = {
    "gemini-3.5-flash-lite": {
        "display_name": "Gemini 3.5 Flash-Lite",
        "input_per_m": 0.075,      # $0.075 per 1M input tokens
        "output_per_m": 0.30,      # $0.30 per 1M output tokens
        "audio_per_sec": 0.000020, # ~$0.0012 per minute audio
        "tier": "Ultra Budget (Lowest Cost)",
        "cost_rank": 1,
        "speed_rating": 5
    },
    "gemini-3.5-flash": {
        "display_name": "Gemini 3.5 Flash",
        "input_per_m": 0.15,       # $0.15 per 1M input tokens
        "output_per_m": 0.60,      # $0.60 per 1M output tokens
        "audio_per_sec": 0.000040, # ~$0.0024 per minute audio
        "tier": "Balanced Budget",
        "cost_rank": 2,
        "speed_rating": 4
    },
    "gemini-3.6-flash": {
        "display_name": "Gemini 3.6 Flash",
        "input_per_m": 0.15,
        "output_per_m": 0.60,
        "audio_per_sec": 0.000040,
        "tier": "Advanced Polish & Synthesis",
        "cost_rank": 2,
        "speed_rating": 4
    },
    "gemini-flash-latest": {
        "display_name": "Gemini Flash Latest",
        "input_per_m": 0.15,
        "output_per_m": 0.60,
        "audio_per_sec": 0.000040,
        "tier": "Balanced Production",
        "cost_rank": 2,
        "speed_rating": 4
    },
    "gemini-3.7-flash": {
        "display_name": "Gemini 3.7 Flash",
        "input_per_m": 0.25,
        "output_per_m": 1.00,
        "audio_per_sec": 0.000050, # ~$0.0030 per minute audio
        "tier": "Advanced Reasoning / Code",
        "cost_rank": 3,
        "speed_rating": 3
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "input_per_m": 0.15,
        "output_per_m": 0.60,
        "audio_per_sec": 0.000040,
        "tier": "Standard Flash",
        "cost_rank": 2,
        "speed_rating": 3
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "input_per_m": 1.25,       # $1.25 per 1M input tokens
        "output_per_m": 5.00,       # $5.00 per 1M output tokens
        "audio_per_sec": 0.000200, # ~$0.0120 per minute audio
        "tier": "Deep Thought / Pro",
        "cost_rank": 4,
        "speed_rating": 2
    }
}

# Standard average typing speed baseline for time savings calculations
TYPING_WORDS_PER_MINUTE = 40.0


@dataclass
class MilestoneInfo:
    rank_title: str
    icon: str
    description: str
    current_words: int
    current_milestone_words: int
    next_milestone_title: str
    next_milestone_words: int
    progress_pct: float
    words_remaining: int


MILESTONES_TABLE: List[Tuple[int, str, str, str]] = [
    (50000, "📖 Grand Novelist", "Full-Length Book / Novel", "You have dictated over 50,000 words — equivalent to writing a complete full-length novel!"),
    (20000, "📚 Prolific Author", "Book Chapter / Novella", "You have spoken over 20,000 words — the length of a major book chapter or novella!"),
    (10000, "📰 Feature Journalist", "Full Magazine / Journal Issue", "You have dictated over 10,000 words — equivalent to writing an entire magazine issue!"),
    (5000, "📝 Academic Scholar", "Academic Essay / Research Paper", "You have completed over 5,000 words — the scope of a full published academic research paper!"),
    (2500, "📑 Technical Specialist", "Technical Whitepaper / Specification", "You have spoken over 2,500 words — equivalent to a comprehensive technical whitepaper!"),
    (1000, "📄 Prolific Writer", "Full Blog Post / Long-form Article", "You have dictated over 1,000 words — equivalent to a complete in-depth blog post!"),
    (500, "📜 Executive Contributor", "Executive Memo / Project Brief", "You have spoken over 500 words — equivalent to an executive project brief!"),
    (100, "💬 Voice Initiate", "Short Dictations & Notes", "You have dictated over 100 words — your voice productivity journey is underway!"),
    (0, "🎙️ Voice Novice", "Getting Started", "Start dictating to unlock voice writing milestones!")
]


def format_duration(seconds: float) -> str:
    """Formats raw seconds into human-friendly duration strings (e.g., '1h 24m', '42 mins', '15s')."""
    total_sec = max(0, int(round(seconds)))
    if total_sec < 60:
        return f"{total_sec}s"
    minutes = total_sec // 60
    secs = total_sec % 60
    if minutes < 60:
        if secs > 0:
            return f"{minutes}m {secs}s"
        return f"{minutes} mins"
    hours = minutes // 60
    rem_mins = minutes % 60
    if rem_mins > 0:
        return f"{hours}h {rem_mins}m"
    return f"{hours} hours"


def calculate_entry_cost(
    model_name: str,
    duration_sec: float = 0.0,
    input_chars: int = 0,
    output_chars: int = 0
) -> float:
    """Calculates estimated API cost in USD for a single Gemini invocation."""
    clean_model = model_name.strip().lower() if model_name else "gemini-3.5-flash-lite"
    pricing = MODEL_PRICING.get(clean_model, MODEL_PRICING["gemini-3.5-flash-lite"])

    # Estimate tokens (~4 characters per token average)
    input_tokens = max(1, input_chars // 4)
    output_tokens = max(1, output_chars // 4)

    token_cost = (input_tokens * (pricing["input_per_m"] / 1_000_000.0)) + \
                 (output_tokens * (pricing["output_per_m"] / 1_000_000.0))

    audio_cost = duration_sec * pricing["audio_per_sec"] if duration_sec > 0 else 0.0
    return token_cost + audio_cost


def get_milestone_info(total_words: int) -> MilestoneInfo:
    """Calculates user's current publication milestone and progress to next level."""
    words = max(0, total_words)
    current_tier = MILESTONES_TABLE[-1]
    next_tier = MILESTONES_TABLE[0]

    for idx, tier in enumerate(MILESTONES_TABLE):
        if words >= tier[0]:
            current_tier = tier
            next_tier = MILESTONES_TABLE[idx - 1] if idx > 0 else tier
            break

    curr_words_threshold = current_tier[0]
    next_words_threshold = next_tier[0]

    if next_words_threshold > curr_words_threshold:
        span = next_words_threshold - curr_words_threshold
        progress = (words - curr_words_threshold) / span
        progress_pct = max(0.0, min(100.0, progress * 100.0))
        words_remaining = max(0, next_words_threshold - words)
    else:
        progress_pct = 100.0
        words_remaining = 0

    return MilestoneInfo(
        rank_title=f"{current_tier[1]} ({current_tier[2]})",
        icon=current_tier[1].split()[0],
        description=current_tier[3],
        current_words=words,
        current_milestone_words=curr_words_threshold,
        next_milestone_title=f"{next_tier[1]} ({next_tier[2]})",
        next_milestone_words=next_words_threshold,
        progress_pct=round(progress_pct, 1),
        words_remaining=words_remaining
    )


class CostAwarenessTracker:
    """Aggregates real-time and historical analytics across Today, This Week, and All-Time."""

    @classmethod
    def get_aggregated_stats(cls, history_list: List[Dict[str, Any]], current_api_key: Optional[str] = None) -> Dict[str, Any]:
        """Processes historical JSON entries and produces comprehensive temporal analytics with per-API-key quota tracking."""
        today_date = datetime.date.today()
        # ISO week start (Monday)
        week_start_date = today_date - datetime.timedelta(days=today_date.weekday())

        curr_tag = (current_api_key or "")[-8:] if (current_api_key and len(current_api_key) >= 8) else None

        today_entries: List[Dict[str, Any]] = []
        week_entries: List[Dict[str, Any]] = []
        all_entries: List[Dict[str, Any]] = []

        for entry in (history_list or []):
            ts_str = entry.get("timestamp", "")
            if not ts_str:
                continue

            entry_tag = entry.get("api_key_tag")
            if curr_tag and entry_tag and entry_tag != "default" and entry_tag != curr_tag:
                continue

            all_entries.append(entry)
            try:
                entry_date = datetime.datetime.fromisoformat(ts_str).date()
                if entry_date == today_date:
                    today_entries.append(entry)
                if entry_date >= week_start_date:
                    week_entries.append(entry)
            except Exception:
                pass

        def _compute_bucket_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
            dictations = 0
            transformations = 0
            total_words = 0
            total_speaking_sec = 0.0
            total_cost_usd = 0.0
            model_usage: Dict[str, int] = {}
            model_costs: Dict[str, float] = {}

            for e in entries:
                mode = (e.get("mode", "") or "clean_dictation").strip()
                is_transform = (
                    "transform" in mode.lower() or
                    mode.upper() in (
                        "IMPROVE", "FIX_GRAMMAR", "PROFESSIONAL", "CASUAL", "CONCISE",
                        "EXPAND", "SUMMARIZE", "EXPLAIN", "TECHNICAL", "CONVERT_PROMPT",
                        "PROMPT_ENHANCER", "SMART_POLISH", "CODE_ASSISTANT", "CODE"
                    ) or
                    mode.lower() in (
                        "prompt_generation", "prompt_enhancer", "smart_polish",
                        "code_assistant", "code"
                    )
                )
                if is_transform:
                    transformations += 1
                else:
                    dictations += 1

                text = e.get("text", "")
                raw_text = e.get("raw_text", "")
                primary_text = text or raw_text
                w_count = len(primary_text.split()) if primary_text else 0
                total_words += w_count

                dur = float(e.get("duration", 0.0) or 0.0)
                total_speaking_sec += dur

                model = e.get("model", "gemini-3.5-flash-lite")
                model_usage[model] = model_usage.get(model, 0) + 1

                cost = calculate_entry_cost(
                    model_name=model,
                    duration_sec=dur,
                    input_chars=len(raw_text or text),
                    output_chars=len(text)
                )
                total_cost_usd += cost
                model_costs[model] = model_costs.get(model, 0.0) + cost

            # Token calculations (Audio: ~25 tokens/sec, Text: ~1.35 tokens/word)
            audio_tokens = int(total_speaking_sec * 25)
            text_tokens = int(total_words * 1.35)
            total_tokens_used = audio_tokens + text_tokens

            # Daily Free Tier Quota (1,000,000 tokens / day per API key)
            daily_quota = 1_000_000
            tokens_remaining = max(0, daily_quota - total_tokens_used)
            tokens_remaining_pct = (tokens_remaining / daily_quota) * 100.0

            # Time Saved vs Manual Typing (at 40 WPM)
            typing_seconds = (total_words / TYPING_WORDS_PER_MINUTE) * 60.0
            net_time_saved_sec = max(0.0, typing_seconds - total_speaking_sec)
            speedup = (typing_seconds / max(1.0, total_speaking_sec)) if total_speaking_sec > 0 else 3.75

            milestone_bucket = get_milestone_info(total_words)

            return {
                "dictations": dictations,
                "transformations": transformations,
                "total_requests": len(entries),
                "total_words": total_words,
                "total_speaking_sec": total_speaking_sec,
                "speaking_time_str": format_duration(total_speaking_sec),
                "typing_time_str": format_duration(typing_seconds),
                "time_saved_sec": net_time_saved_sec,
                "time_saved_str": format_duration(net_time_saved_sec),
                "speedup_multiplier": f"{speedup:.1f}x",
                "estimated_cost_usd": total_cost_usd,
                "cost_formatted": f"${total_cost_usd:.4f}" if total_cost_usd >= 0.0001 else "< $0.0001 (Free Tier)",
                "tokens_used": total_tokens_used,
                "tokens_used_str": f"{total_tokens_used:,} tokens",
                "tokens_left": tokens_remaining,
                "tokens_left_str": f"{tokens_remaining:,} ({tokens_remaining_pct:.1f}% Left)",
                "milestone": milestone_bucket,
                "milestone_title": milestone_bucket.rank_title,
                "milestone_desc": milestone_bucket.description,
                "model_usage": model_usage,
                "model_costs": model_costs
            }

        # Filter today's token usage specifically for the current active API key
        today_active_key_entries = [
            e for e in today_entries
            if not curr_tag or not e.get("api_key_tag") or e.get("api_key_tag") == "default" or e.get("api_key_tag") == curr_tag
        ]

        today_metrics = _compute_bucket_metrics(today_entries)
        week_metrics = _compute_bucket_metrics(week_entries)
        all_metrics = _compute_bucket_metrics(all_entries)

        # Overwrite today's token quota with active key's specific usage
        if curr_tag:
            active_audio_sec = sum(float(e.get("duration", 0.0) or 0.0) for e in today_active_key_entries)
            active_words = sum(len((e.get("text") or e.get("raw_text") or "").split()) for e in today_active_key_entries)
            active_tokens_used = int(active_audio_sec * 25) + int(active_words * 1.35)
            active_tokens_left = max(0, 1_000_000 - active_tokens_used)
            active_tokens_pct = (active_tokens_left / 1_000_000) * 100.0
            today_metrics["tokens_used"] = active_tokens_used
            today_metrics["tokens_used_str"] = f"{active_tokens_used:,} tokens"
            today_metrics["tokens_left"] = active_tokens_left
            today_metrics["tokens_left_str"] = f"{active_tokens_left:,} ({active_tokens_pct:.1f}% Left)"

        # Context-aware display for weekly and all-time quota
        week_metrics["tokens_left_str"] = "Resets Daily at 00:00 UTC"
        all_metrics["tokens_left_str"] = "Free Tier (1M/day Quota)"

        milestone = get_milestone_info(all_metrics["total_words"])

        return {
            "today": today_metrics,
            "this_week": week_metrics,
            "all_time": all_metrics,
            "milestone": milestone
        }


# extractor.py — Pure-Python fallback (no spaCy / NumPy)
# Minimal multi-word expression (MWE) detection used by the engine.
# Returns simple spans with lightweight "confidence" so the rest of the pipeline works.

from __future__ import annotations
from typing import List, Dict

class Span:
    def __init__(self, span_tokens, start_token, end_token, duration_data=None, span_type="MWE", confidence=0.8):
        self.span_tokens = span_tokens
        self.start_token = start_token
        self.end_token = end_token
        self.duration_data = duration_data or {}
        self.type = span_type
        self.confidence = confidence

class MWEExtractor:
    """
    Heuristic detector:
      - progressive / perfect constructions like "has been running"
      - simple supply/movement phrases like "advance to", "fall back", "dig in"
      - rest/refit cues
    This is intentionally simple; it avoids spaCy/NumPy to keep the game runnable.
    """
    PHRASES = [
        ("has been", "duration"),
        ("have been", "duration"),
        ("been running", "duration"),
        ("advance to", "move"),
        ("attack", "attack"),
        ("fall back", "fallback"),
        ("dig in", "defensive"),
        ("hold position", "defensive"),
        ("rest", "rest"),
        ("refit", "refit"),
        ("resupply", "supply"),
    ]

    def extract(self, sentence: str) -> List[Span]:
        toks = sentence.strip().split()
        ltoks = [t.lower() for t in toks]
        spans: List[Span] = []

        def add_span(i0, i1, typ, conf=0.9, extra=None):
            spans.append(Span(
                span_tokens=toks[i0:i1],
                start_token=i0,
                end_token=i1-1,
                duration_data={"type": typ, **(extra or {})},
                span_type=typ.upper(),
                confidence=conf
            ))

        # bigram/phrase scan
        for i in range(len(ltoks)):
            bi = " ".join(ltoks[i:i+2])
            tri = " ".join(ltoks[i:i+3])
            for pat, typ in self.PHRASES:
                if pat == bi:
                    add_span(i, i+2, typ)
                elif pat == tri:
                    add_span(i, i+3, typ)

        # simple tense cue: "... has been <verb>ing"
        for i in range(len(ltoks)-2):
            if ltoks[i] in ("has", "have") and ltoks[i+1] == "been" and ltoks[i+2].endswith("ing"):
                add_span(i, i+3, "duration", conf=0.85, extra={"progressive": True})

        # If nothing matched, still emit a very low-confidence generic span so downstream UI shows something
        if not spans and toks:
            spans.append(Span(
                span_tokens=toks[: min(3, len(toks))],
                start_token=0,
                end_token=min(2, len(toks)-1),
                duration_data={"type":"generic"},
                span_type="MWE",
                confidence=0.3,
            ))
        return spans

from duration_utils import compute_span_duration

class MWESpan:
    def __init__(self, start_idx, end_idx, tokens, span_type="unspecified"):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.tokens = tokens
        self.span_type = span_type
        self.duration_data = self._compute_duration()

    def _compute_duration(self):
        result = compute_span_duration((self.start_idx, self.end_idx), self.tokens)
        result["type"] = self.span_type
        return result

    def __repr__(self):
        return f"<MWESpan {self.duration_data}>"

    def __eq__(self, other):
        return self.duration_data == other.duration_data

    def __hash__(self):
        return hash(tuple(self.duration_data["span_tokens"]))

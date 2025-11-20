def compute_span_duration(span, tokens):
    """
    Compute the duration of a span within a token sequence.

    Parameters:
    - span: tuple(int, int), the (start_idx, end_idx) for the MWE span
    - tokens: list of str, the tokenized sentence

    Returns:
    - dict: duration data including length, tokens in span, and start/end words
    """
    start, end = span
    if not (0 <= start < len(tokens)) or not (0 <= end < len(tokens)) or start > end:
        raise ValueError(f"Invalid span ({start}, {end}) for token list of length {len(tokens)}.")

    span_tokens = tokens[start:end + 1]
    duration = end - start + 1  # inclusive

    return {
        "duration": duration,
        "start_token": tokens[start],
        "end_token": tokens[end],
        "span_tokens": span_tokens
    }

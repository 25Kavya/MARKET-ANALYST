from phase9.cache_key import compute_cache_key, normalize_query


def test_normalize_collapses_case_whitespace_and_punctuation():
    assert normalize_query("How's Infosys doing?") == normalize_query("how s infosys doing")
    assert normalize_query("  Infosys   stock   ") == normalize_query("infosys stock")


def test_cache_key_same_for_trivial_rephrasing():
    key_a = compute_cache_key("classify_intent_mode", "How's Infosys doing?", "v1")
    key_b = compute_cache_key("classify_intent_mode", "  how's infosys doing  ", "v1")

    assert key_a == key_b


def test_cache_key_differs_for_genuinely_different_phrasing():
    # Documented trade-off: true paraphrases are NOT collapsed by this cache —
    # only trivial rephrasing (case/whitespace/punctuation) is. Achieving
    # semantic collapsing would need embedding-based matching, which this
    # design intentionally doesn't build.
    key_a = compute_cache_key("classify_intent_mode", "how's infosys doing", "v1")
    key_b = compute_cache_key("classify_intent_mode", "what's infosys stock status", "v1")

    assert key_a != key_b


def test_cache_key_differs_by_tool_name():
    key_a = compute_cache_key("tool_a", "same query", "v1")
    key_b = compute_cache_key("tool_b", "same query", "v1")

    assert key_a != key_b


def test_cache_key_differs_by_prompt_version():
    key_a = compute_cache_key("classify_intent_mode", "same query", "v1")
    key_b = compute_cache_key("classify_intent_mode", "same query", "v2")

    assert key_a != key_b

import hashlib
import re
import string

_PUNCTUATION_RE = re.compile(f"[{re.escape(string.punctuation)}]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(query):
    """Lowercase, strip punctuation, and collapse whitespace so trivial
    rephrasing (case, extra spaces, punctuation) hits the same cache entry.

    This intentionally does NOT collapse genuine paraphrases ("how's infosys
    doing" vs "what's infosys stock status") into the same key — that would
    need semantic/embedding matching, which this cache doesn't attempt.
    """
    text = query.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def compute_cache_key(tool_name, query, prompt_version):
    normalized = normalize_query(query)
    digest_input = f"{tool_name}:{prompt_version}:{normalized}"
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

import json
import time
from datetime import datetime
from pathlib import Path
from livekit.agents.llm import ChatContext, ChatMessage, ChatRole

# ── File paths ──────────────────────────────────────────────────────────────
MEMORY_DIR        = Path("heart_data")
CONVO_LOG_FILE    = MEMORY_DIR / "conversation_log.json"   # full history – never pruned
SMART_MEMORY_FILE = MEMORY_DIR / "smart_memory.json"       # scored highlights
BACKUP_EXT        = ".bak"

MEMORY_DIR.mkdir(exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _ts() -> float:
    return time.time()

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _safe_load(path: Path):
    """Load JSON from path; fall back to .bak; return [] on total failure."""
    for p in (path, path.with_suffix(BACKUP_EXT)):
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Heart Memory] Could not read {p}: {e}")
    return []

def _atomic_save(path: Path, data):
    """Write data safely: temp → backup → replace."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if path.exists():
        path.replace(path.with_suffix(BACKUP_EXT))
    tmp.replace(path)


# ════════════════════════════════════════════════════════════════════════════
#  SCORING & CLASSIFICATION  (used only for smart_memory highlights)
# ════════════════════════════════════════════════════════════════════════════

def score_importance(content: str) -> int:
    c = content.lower()
    if any(k in c for k in ["remember", "important", "never forget", "always"]):
        return 10
    if any(k in c for k in ["goal", "build", "project", "plan"]):
        return 9
    if any(k in c for k in ["prefer", "like", "love", "hate", "habit"]):
        return 8
    if any(k in c for k in ["name", "called", "i am", "i'm"]):
        return 8
    if len(c) > 120:
        return 6
    if len(c) > 60:
        return 5
    return 3


def classify_type(content: str) -> str:
    c = content.lower()
    if "goal" in c or "build" in c or "plan" in c:
        return "goal"
    if "prefer" in c or "like" in c or "love" in c:
        return "preference"
    if "project" in c:
        return "project"
    if "name" in c or "i am" in c or "i'm" in c:
        return "identity"
    return "casual"


# ════════════════════════════════════════════════════════════════════════════
#  FULL CONVERSATION LOG  –  remembers EVERYTHING
# ════════════════════════════════════════════════════════════════════════════

def append_to_log(messages: list):
    """
    Append a list of {role, content} dicts to the permanent conversation log.
    Nothing is ever deleted from this file.
    """
    log = _safe_load(CONVO_LOG_FILE)
    if not isinstance(log, list):
        log = []

    existing_keys = {(m.get("role"), m.get("content")) for m in log}

    for msg in messages:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if not role or not content:
            continue
        if (role, content) in existing_keys:
            continue
        log.append({
            "role":      role,
            "content":   content,
            "timestamp": _ts(),
            "datetime":  _now_str(),
        })
        existing_keys.add((role, content))

    _atomic_save(CONVO_LOG_FILE, log)


def load_full_log() -> list:
    """Return the entire conversation history as a list of dicts."""
    data = _safe_load(CONVO_LOG_FILE)
    return data if isinstance(data, list) else []


def get_recent_log(n_messages: int = 40) -> list:
    """
    Return the last `n_messages` turns from the full log as ChatMessage objects,
    ready to inject into a ChatContext so Heart remembers the recent session.
    """
    log   = load_full_log()
    tail  = log[-n_messages:] if len(log) > n_messages else log
    items = []
    for entry in tail:
        try:
            items.append(
                ChatMessage(
                    role    = ChatRole(entry["role"]),
                    content = entry["content"],
                )
            )
        except Exception:
            continue
    return items


# ════════════════════════════════════════════════════════════════════════════
#  SMART MEMORY  –  scored highlights for quick recall / context injection
# ════════════════════════════════════════════════════════════════════════════

def _evolve_score(item: dict) -> int:
    score = item.get("importance", 5)
    if item.get("used_count", 0) > 3:
        score += 2
    age = _ts() - item.get("timestamp", _ts())
    if age > 7 * 24 * 3600:
        score -= 1          # gentle decay (was -2)
    return max(1, min(score, 10))


def _mark_used(item: dict):
    item["used_count"] = item.get("used_count", 0) + 1
    item["last_used"]  = _ts()


def save_smart_memory(chat_ctx: ChatContext):
    """
    Extract high-importance messages from the current session and merge them
    into smart_memory.json.  Low-importance messages are NOT saved here —
    they still live in the full conversation log.
    """
    existing = _safe_load(SMART_MEMORY_FILE)
    if not isinstance(existing, list):
        existing = []

    existing_keys = {m.get("content", "").strip() for m in existing}
    new_items     = []

    for msg in chat_ctx.items:
        if not (hasattr(msg, "role") and hasattr(msg, "content")):
            continue

        content    = msg.content or ""
        importance = score_importance(content)

        if importance < 6:          # only highlights
            continue
        if content.strip() in existing_keys:
            continue

        new_items.append({
            "role":       msg.role.value if hasattr(msg.role, "value") else str(msg.role),
            "content":    content,
            "importance": importance,
            "type":       classify_type(content),
            "timestamp":  _ts(),
            "datetime":   _now_str(),
            "used_count": 0,
        })
        existing_keys.add(content.strip())

    merged = existing + new_items

    # evolve scores
    for item in merged:
        item["importance"] = _evolve_score(item)

    # prune only truly stale low-value items
    merged = [m for m in merged if m["importance"] >= 3]

    # cap at 500 (keep newest)
    if len(merged) > 500:
        merged = merged[-500:]

    _atomic_save(SMART_MEMORY_FILE, merged)


def get_relevant_memory(query: str, top_k: int = 10) -> list:
    """
    Return the most relevant smart-memory highlights for a query.
    Also checks recent conversation log if smart memory is sparse.
    """
    smart = _safe_load(SMART_MEMORY_FILE)
    if not isinstance(smart, list):
        smart = []

    words    = set(query.lower().split())
    relevant = []

    for m in smart:
        text = m.get("content", "").lower()
        if any(w in text for w in words) and m.get("importance", 0) >= 5:
            _mark_used(m)
            relevant.append(m)

    relevant.sort(key=lambda x: (x["importance"], x.get("used_count", 0)), reverse=True)
    results = relevant[:top_k]

    # if sparse, pad with recent log entries that match the query
    if len(results) < 3:
        log = load_full_log()
        for entry in reversed(log):
            text = entry.get("content", "").lower()
            if any(w in text for w in words):
                results.append(entry)
            if len(results) >= top_k:
                break

    return results


# ════════════════════════════════════════════════════════════════════════════
#  LOAD MEMORY  (called on startup)
# ════════════════════════════════════════════════════════════════════════════

def load_memory(recent_turns: int = 40) -> ChatContext:
    """
    Build a ChatContext pre-loaded with:
      1. The last `recent_turns` messages from the full conversation log
         → Heart picks up exactly where it left off.
      2. Any smart-memory highlights NOT already in that window
         → Key facts / goals are always present.

    Pass recent_turns=0 to skip conversation history (smart-memory only).
    Pass recent_turns=-1 to load the ENTIRE history (careful with large logs).
    """
    # --- recent conversation ---
    if recent_turns == -1:
        log = load_full_log()
    elif recent_turns > 0:
        log = load_full_log()
        log = log[-recent_turns:]
    else:
        log = []

    seen_contents = {e.get("content", "") for e in log}

    # --- smart-memory highlights not already in the window ---
    smart = _safe_load(SMART_MEMORY_FILE)
    smart = [m for m in smart if isinstance(m, dict) and m.get("importance", 0) >= 7]
    smart.sort(key=lambda x: x.get("importance", 0), reverse=True)
    extra = [m for m in smart[:20] if m.get("content", "") not in seen_contents]

    combined = extra + log   # highlights first, then chronological tail

    messages = []
    for entry in combined:
        role    = entry.get("role", "")
        content = entry.get("content", "")
        if not role or not content:
            continue
        try:
            messages.append(
                ChatMessage(
                    role    = ChatRole(role),
                    content = content,
                )
            )
        except Exception:
            continue

    print(f"[Heart Memory] Loaded {len(messages)} messages "
          f"({len(extra)} highlights + {len(log)} recent turns)")
    return ChatContext(items=messages)


# ════════════════════════════════════════════════════════════════════════════
#  UNIFIED SAVE  (call this after every session / at shutdown)
# ════════════════════════════════════════════════════════════════════════════

def save_memory(chat_ctx: ChatContext):
    """
    1. Append ALL messages from this session to the permanent conversation log.
    2. Extract highlights into smart_memory.
    """
    messages = []
    for msg in chat_ctx.items:
        if hasattr(msg, "role") and hasattr(msg, "content"):
            messages.append({
                "role":    msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.content or "",
            })

    append_to_log(messages)
    save_smart_memory(chat_ctx)
    print(f"[Heart Memory] Saved {len(messages)} messages to conversation log.")


# ════════════════════════════════════════════════════════════════════════════
#  STATS / DEBUG
# ════════════════════════════════════════════════════════════════════════════

def memory_stats() -> dict:
    log   = load_full_log()
    smart = _safe_load(SMART_MEMORY_FILE)
    return {
        "total_messages_ever":   len(log),
        "smart_highlights":      len(smart) if isinstance(smart, list) else 0,
        "log_file":              str(CONVO_LOG_FILE),
        "smart_file":            str(SMART_MEMORY_FILE),
        "oldest_message":        log[0].get("datetime")  if log else None,
        "newest_message":        log[-1].get("datetime") if log else None,
    }
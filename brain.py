"""
command_processor.py
──────────────────────────────────────────────────────────────────────────────
Heart's command dispatcher — personality baked in, no separate module.

Flow:
  1. Detect intent from raw text
  2. Ask Heart's LLM (using your existing behaviour prompt) what to do
  3. Heart either runs / tweaks / blocks the command with a voice line
  4. Return combined voice_line + command result to the caller

Fixes applied
─────────────
• Removed heart_personality import (no separate module needed)
• Imports heart_behavior_prompt correctly and aliased as HEART_PROMPT
• _ask_heart() calls the LLM directly using that prompt
• _dispatch() + process_command() are now async to handle async handlers
• _safe_call() transparently awaits async handlers and calls sync ones normally
"""

import json
import re
import inspect
import requests
from datetime import datetime

from intent_parser import detect_intent

# ── Fix 1: correct import — alias to HEART_PROMPT for clean use below ───────
#    If your variable is named differently inside heart_behavior_prompt.py,
#    just change "heart_behavior_prompt" on the right side of the `as`.
from heart_behavior_prompt import HEART_BEHAVIOR_PROMPT as HEART_PROMPT

from system_control import handle_system
from media_control import handle_media
from music_engine import handle_music
from app_manager import handle_apps
from file_manager import handle_files
from weather_time import handle_time
from coding_agent import handle_coding
from pdf_tools import merge_pdfs, summarize_pdf


# ── Put your OpenRouter key here (same one used in heart_email.py) ───────────
OPENROUTER_API_KEY = "YOUR_OPENROUTER_KEY_HERE"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ────────────────────────────────────────────────────────────────────────────
# Fix 2: LLM decision call — uses YOUR existing behaviour prompt directly
# ────────────────────────────────────────────────────────────────────────────

def _ask_heart(command_text: str, category: str, action: str) -> dict:
    """
    Send the command to the LLM with Heart's behaviour prompt as the system
    prompt.  Returns a decision dict telling the dispatcher what to do.
    """
    now = datetime.now()

    user_message = (
        f'User command : "{command_text}"\n'
        f"Intent       : category={category}, action={action}\n"
        f"Current time : {now.strftime('%I:%M %p')}\n"
        f"Late night   : {now.hour >= 22 or now.hour < 5}\n\n"
        "Decide how to respond as Heart.  "
        "Return ONLY valid JSON — no markdown, no extra text:\n"
        "{\n"
        '  "execute_original" : true | false,\n'
        '  "override_category": "<category string or null>",\n'
        '  "override_action"  : "<action string or null>",\n'
        '  "override_text"    : "<modified command text or null>",\n'
        '  "voice_line"       : "<what Heart says out loud, empty string if nothing to add>"\n'
        "}\n\n"
        'Use "block" as override_category to refuse the command entirely.\n'
        "execute_original=false means Heart overrides; use override_* to say what runs instead."
    )

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "max_tokens": 300,
                "messages": [
                    {"role": "system", "content": HEART_PROMPT},   # <── your prompt
                    {"role": "user",   "content": user_message},
                ],
            },
            timeout=6,
        )
        raw   = resp.json()["choices"][0]["message"]["content"]
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(clean)

    except Exception as exc:
        print(f"[heart] _ask_heart failed: {exc}")
        return {
            "execute_original" : True,
            "override_category": None,
            "override_action"  : None,
            "override_text"    : None,
            "voice_line"       : "",
        }


# ────────────────────────────────────────────────────────────────────────────
# Fix 3: transparent async/sync helper
# Handles the "Expected type 'str', got 'Coroutine'" errors — works whether
# a handler is async or plain sync, no changes needed in any handler file.
# ────────────────────────────────────────────────────────────────────────────

async def _safe_call(fn, *args) -> str:
    """Call fn(*args); await the result only if fn is a coroutine function."""
    result = fn(*args)
    if inspect.isawaitable(result):
        return await result
    return result


# ────────────────────────────────────────────────────────────────────────────
# Dispatcher — maps category/action → correct handler
# ────────────────────────────────────────────────────────────────────────────

async def _dispatch(category: str, action: str, text: str) -> str:
    """Execute a command by category and return its result string."""

    if category == "system":
        return await _safe_call(handle_system, text)

    if category == "media":
        return await _safe_call(handle_media, text)

    if category == "music":
        return await _safe_call(handle_music, text)

    if category == "apps":
        return await _safe_call(handle_apps, text)

    if category == "files":
        return await _safe_call(handle_files, text)

    if category == "time":
        return await _safe_call(handle_time)          # no text arg needed

    if category == "coding":
        return await _safe_call(handle_coding, text)

    if category == "pdf":
        if action == "merge":
            return await _safe_call(merge_pdfs, "a.pdf", "b.pdf", "merged.pdf")
        if action == "summarize":
            return await _safe_call(summarize_pdf, "file.pdf")

    return "Command not understood"


# ────────────────────────────────────────────────────────────────────────────
# Public entry point
# ────────────────────────────────────────────────────────────────────────────

async def process_command(text: str) -> str:
    """
    Process a raw voice/text command through Heart's full pipeline.

    Returns a single string — Heart's voice_line (if any) followed by
    the functional result of whichever command was executed.
    """

    # ── Step 1: detect intent ────────────────────────────────────────────────
    intent    = detect_intent(text)
    category  = intent.get("category", "unknown")
    action    = intent.get("action",   "")
    user_text = intent.get("text",     text)

    # ── Step 2: ask Heart what to do (uses your behaviour prompt) ────────────
    decision = _ask_heart(user_text, category, action)

    execute_original  = decision.get("execute_original",  True)
    override_category = decision.get("override_category", None)
    override_action   = decision.get("override_action",   None)
    override_text     = decision.get("override_text",     None)
    voice_line        = decision.get("voice_line",        "")

    # ── Step 3: build the response ───────────────────────────────────────────
    parts: list[str] = []

    if voice_line:
        parts.append(voice_line)

    if execute_original:
        # Run the user's original command
        cmd_result = await _dispatch(category, action, user_text)
        if cmd_result:
            parts.append(cmd_result)

    else:
        # Heart is overriding
        eff_category = override_category or category
        eff_action   = override_action   or action
        eff_text     = override_text     or user_text

        if eff_category != "block":
            # "block" = refuse entirely; voice_line already said everything
            cmd_result = await _dispatch(eff_category, eff_action, eff_text)
            if cmd_result:
                parts.append(cmd_result)

    # ── Step 4: return ───────────────────────────────────────────────────────
    return "  ".join(filter(None, parts))

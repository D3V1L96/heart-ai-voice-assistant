import os
import datetime
from textwrap import dedent
from dotenv import load_dotenv

# Your ide_manager module (assuming you have these functions)
from ide_manager import (
    detect_installed_ides,     # ← this was missing/unresolved
    detect_running_ide,
    launch_ide,
    open_notepad
)

# ────────────────────────────────────────────────
# Hardcoded OpenRouter API key (no .env needed)
# ────────────────────────────────────────────────
OPENROUTER_API_KEY = "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"

# ────────────────────────────────────────────────
# Save folder on Desktop (safe, no permission issues)
# ────────────────────────────────────────────────
SAVE_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "HeartCode")
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ────────────────────────────────────────────────
# OpenRouter Client
# ────────────────────────────────────────────────
from openai import OpenAI

llm_client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

DEFAULT_MODEL = "kwaipilot/kat-coder-pro-v2"   # Working model on OpenRouter

# ────────────────────────────────────────────────
# Generate fully dynamic code using LLM
# ────────────────────────────────────────────────
def generate_code_with_llm(user_request: str, language: str) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": dedent(f"""\
                    You are an expert {language} developer.
                    Generate **complete, runnable code** based on the user's request.
                    Reply **ONLY** with clean source code.
                    No explanations, no markdown fences, no intro/ending text.
                    Just pure code + minimal helpful comments.
                    Use modern syntax and best practices.""")
            },
            {
                "role": "user",
                "content": f"Language: {language}\n\nRequest:\n{user_request}"
            }
        ]

        response = llm_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            top_p=0.95,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"# LLM call failed\n# {type(e).__name__}: {str(e)}"


# ────────────────────────────────────────────────
# Intent & Language Detection
# ────────────────────────────────────────────────
def is_coding_request(text: str) -> bool:
    t = text.lower()
    coding_keywords = [
        "code", "program", "script", "function", "class", "write", "likho",
        "banao", "kar do", "create", "make", "coding", "generate"
    ]
    return any(kw in t for kw in coding_keywords)


def detect_language(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["python", "py ", ".py", "pip ", "import ", "def "]):
        return "python"
    if any(x in t for x in ["bash", "shell", "sh ", "#!", "bash script"]):
        return "bash"
    if any(x in t for x in ["c#", "csharp", ".cs", "console.writeline", "namespace "]):
        return "csharp"
    if any(x in t for x in ["javascript", "js ", "node ", "react", "console.log"]):
        return "javascript"
    if any(x in t for x in ["java ", "public static", "system.out", ".java"]):
        return "java"
    if any(x in t for x in ["c++", "cpp", "#include", "std::", "cout", ".cpp"]):
        return "cpp"

    return "python"  # default


# ────────────────────────────────────────────────
# Main Handler – fully async, dynamic, asks user for editor
# ────────────────────────────────────────────────
async def handle_coding(text: str) -> str:
    if not text.strip():
        return "Sir, koi coding instruction nahi diya."

    if not is_coding_request(text):
        return dedent("""\
            Sir, yeh coding request jaisa nahi lag raha.

            Examples jo samajh mein aayenge:
            • python mein calculator bana do
            • javascript mein async fetch API call
            • c# mein student class with marks
            • bash script jo old files delete kare

            Ab batao, kya code banwana hai?""")

    language = detect_language(text)
    code = generate_code_with_llm(text, language)

    # Save code to file safely
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "py" if language.lower() == "python" else "js" if language.lower() == "javascript" else "txt"
    filename = f"Heart_Code_{ts}.{ext}"
    path = os.path.join(SAVE_FOLDER, filename)

    try:
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as save_err:
        return f"Code generated but failed to save file.\nError: {save_err}\n\n``` {language}\n{code[:600]}...\n```"

    # Detect installed/running IDEs
    running = detect_running_ide()
    installed = detect_installed_ides()

    # Ask user where to open
    editor_options = []
    if running:
        editor_options.append(f"Running IDE: {running}")
    if installed:
        editor_options.append(f"Installed IDEs: {', '.join(installed)}")
    editor_options.append("Notepad")

    options_str = "\n".join([f"- {opt}" for opt in editor_options])

    return dedent(f"""\
        Code successfully generated in **{language}**!
        Saved at: {path}

        **Kisme kholna chahte ho?**
        {options_str}

        Batao: "open in vs code", "notepad mein kholo", "open in pycharm", etc.
        Ya kuch aur batao!""")

# ────────────────────────────────────────────────
# Standalone test mode (run this file alone to test)
# ────────────────────────────────────────────────
if __name__ == "__main__":
    async def test():
        test_requests = [
            "python mein simple calculator bana do",
            "javascript mein fetch API call with error handling",
            "c# mein student class with name, roll number, marks"
        ]

        for req in test_requests:
            print(f"\n=== Testing: {req} ===")
            result = await handle_coding(req)
            print(result)
            print("=" * 60)


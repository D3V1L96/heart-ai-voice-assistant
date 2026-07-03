# ==========================================
# voice_auth.py
# H.E.A.R.T VOICE SECURITY SYSTEM
# PERSISTENT + FAST + RESTART SAFE
# ==========================================

import os
import gc
import time
import pickle
import ctypes
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

# ==========================================
# PERFORMANCE SETTINGS
# ==========================================

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# ==========================================
# CONFIG
# ==========================================

BASE_DIR = Path(__file__).parent.resolve()

SECURITY_DIR = BASE_DIR / "security"
SECURITY_DIR.mkdir(parents=True, exist_ok=True)

MODEL_DIR = str(BASE_DIR / "models" / "voice_auth")

SAMPLE_RATE = 16000

# FAST + STABLE
RECORD_SECONDS = 2.5

# LOWERED FOR REAL-WORLD CONDITIONS
VOICE_THRESHOLD = 0.30

# REDUCED TO PREVENT AUDIO DISTORTION
GAIN = 1.2

# MIC STABILIZATION AFTER RESTART
MIC_WARMUP_DELAY = 1.5

OWNER_WAV = SECURITY_DIR / "owner.wav"
AUTH_WAV = SECURITY_DIR / "auth.wav"

EMBED_FILE = SECURITY_DIR / "owner_embedding.pkl"

# ==========================================
# GLOBAL STATE
# ==========================================

STATE = {
    "torch": None,
    "torchaudio": None,
    "verification": None,
    "device": "cpu",
    "owner_embedding": None,
    "failed": 0,
    "lock_until": 0,
    "engine_loaded": False,
}

# ==========================================
# UTILS
# ==========================================

def now():
    return int(time.time())


def is_locked():
    return now() < STATE["lock_until"]


def lock_system():

    STATE["lock_until"] = now() + 120

    print("\n🔒 SYSTEM LOCKED FOR 2 MINUTES")

    try:
        ctypes.windll.user32.LockWorkStation()

    except Exception:
        pass


# ==========================================
# SAFE PICKLE SAVE
# ==========================================

def safe_save_pickle(path, data):

    temp_path = str(path) + ".tmp"

    with open(temp_path, "wb") as f:

        pickle.dump(data, f)

        f.flush()

        os.fsync(f.fileno())

    os.replace(temp_path, path)


# ==========================================
# ENGINE LOADER
# ==========================================

def load_engine():

    if STATE["engine_loaded"]:
        return

    print("[VOICE AUTH] Loading AI engine...")

    import torch
    import torchaudio

    from speechbrain.inference.speaker import (
        SpeakerRecognition
    )

    # ======================================
    # THREAD OPTIMIZATION
    # ======================================

    torch.set_num_threads(1)

    # ======================================
    # DEVICE
    # ======================================

    if torch.cuda.is_available():

        device = "cuda"

        torch.backends.cudnn.benchmark = True

    else:

        device = "cpu"

    # ======================================
    # LOAD MODEL
    # ======================================

    verification = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=MODEL_DIR,
        run_opts={"device": device}
    )

    STATE["torch"] = torch
    STATE["torchaudio"] = torchaudio
    STATE["verification"] = verification
    STATE["device"] = device
    STATE["engine_loaded"] = True

    print(f"[VOICE AUTH] READY ({device.upper()})")


# ==========================================
# RECORD VOICE
# ==========================================

def record_voice(path):

    try:
        sd.stop()

    except Exception:
        pass

    print("\n🎤 Speak...")

    # ======================================
    # RECORD
    # ======================================

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )

    sd.wait()

    # ======================================
    # AUDIO BOOST
    # ======================================

    audio = np.clip(audio * GAIN, -1, 1)

    # ======================================
    # REMOVE SILENCE
    # ======================================

    volume = np.abs(audio)

    mask = volume > 0.015

    if np.any(mask):

        indices = np.where(mask)[0]

        start = max(0, indices[0] - 1000)
        end = min(len(audio), indices[-1] + 1000)

        audio = audio[start:end]

    # ======================================
    # SAVE AUDIO
    # ======================================

    sf.write(str(path), audio, SAMPLE_RATE)

    return path


# ==========================================
# PROCESS AUDIO
# ==========================================

def process_audio(path):

    load_engine()

    torch = STATE["torch"]
    torchaudio = STATE["torchaudio"]

    wav, sr = sf.read(str(path))

    # ======================================
    # FORCE MONO
    # ======================================

    if len(wav.shape) == 2:

        wav = wav.mean(axis=1)

    wav = wav.astype(np.float32)

    # ======================================
    # NORMALIZE
    # ======================================

    peak = np.max(np.abs(wav)) + 1e-6

    wav = wav / peak

    # ======================================
    # TORCH
    # ======================================

    wav = torch.from_numpy(wav).unsqueeze(0)

    # ======================================
    # RESAMPLE
    # ======================================

    if sr != SAMPLE_RATE:

        wav = torchaudio.transforms.Resample(
            sr,
            SAMPLE_RATE
        )(wav)

    return wav.to(STATE["device"])


# ==========================================
# CREATE EMBEDDING
# ==========================================

def create_embedding(path):

    load_engine()

    torch = STATE["torch"]

    wav = process_audio(path)

    with torch.no_grad():

        emb = STATE["verification"].encode_batch(wav)

    return emb.cpu()


# ==========================================
# SAVE EMBEDDING
# ==========================================

def save_embedding(embedding):

    try:

        safe_save_pickle(EMBED_FILE, embedding)

        print("[VOICE AUTH] Voice profile saved permanently")

        return True

    except Exception as e:

        print("[SAVE ERROR]", e)

        return False


# ==========================================
# LOAD EMBEDDING
# ==========================================

def load_embedding():

    if not EMBED_FILE.exists():

        print("[VOICE AUTH] No saved voice profile")

        return None

    try:

        with open(EMBED_FILE, "rb") as f:

            embedding = pickle.load(f)

        print("[VOICE AUTH] Saved owner profile loaded")

        return embedding

    except Exception as e:

        print("[LOAD ERROR]", e)

        return None


# ==========================================
# ENROLL OWNER
# ==========================================

def enroll_owner():

    print("\n================================")
    print("🔐 OWNER VOICE ENROLLMENT")
    print("================================")

    # ======================================
    # MIC WARMUP
    # ======================================

    time.sleep(MIC_WARMUP_DELAY)

    record_voice(OWNER_WAV)

    embedding = create_embedding(OWNER_WAV)

    STATE["owner_embedding"] = embedding

    saved = save_embedding(embedding)

    if saved:

        print("\n✅ OWNER REGISTERED SUCCESSFULLY")
        print("✅ Voice profile persisted permanently")

    else:

        print("\n❌ Failed to save owner profile")


# ==========================================
# VERIFY VOICE
# ==========================================

def verify_voice(path):

    if is_locked():

        print("[SECURITY] SYSTEM TEMP LOCKED")

        return False

    try:

        torch = STATE["torch"]

        # ==================================
        # CHECK OWNER
        # ==================================

        if STATE["owner_embedding"] is None:

            print("[VOICE AUTH] No owner enrolled")

            return False

        # ==================================
        # CURRENT EMBEDDING
        # ==================================

        current = create_embedding(path)

        owner = STATE["owner_embedding"]

        # ==================================
        # COSINE SIMILARITY
        # ==================================

        score = torch.nn.functional.cosine_similarity(
            owner.squeeze(),
            current.squeeze(),
            dim=0
        ).item()

        print(f"[VOICE SCORE] {score:.4f}")

        # ==================================
        # SUCCESS
        # ==================================

        if score >= VOICE_THRESHOLD:

            STATE["failed"] = 0

            print("✅ ACCESS GRANTED")

            return True

        # ==================================
        # FAILED
        # ==================================

        STATE["failed"] += 1

        print("❌ ACCESS DENIED")

        remaining = 3 - STATE["failed"]

        if remaining > 0:

            print(f"[SECURITY] Attempts left: {remaining}")

        # ==================================
        # LOCK SYSTEM
        # ==================================

        if STATE["failed"] >= 3:

            lock_system()

        return False

    except Exception as e:

        print("[VERIFY ERROR]", e)

        STATE["failed"] += 1

        return False


# ==========================================
# AUTH FLOW
# ==========================================

def authenticate_once():

    load_engine()

    # ======================================
    # CHECK ENROLLMENT
    # ======================================

    if STATE["owner_embedding"] is None:

        print("[VOICE AUTH] No enrolled owner")
        print("[VOICE AUTH] Please enroll first")

        return False

    # ======================================
    # MIC WARMUP AFTER BOOT
    # ======================================

    time.sleep(MIC_WARMUP_DELAY)

    # ======================================
    # RECORD AUTH
    # ======================================

    record_voice(AUTH_WAV)

    return verify_voice(AUTH_WAV)


# ==========================================
# RESET VOICE
# ==========================================

def reset_voice(confirm=False):

    if not confirm:

        print("\n⚠️ WARNING")
        print("This deletes all voice profiles.")
        print("Run reset_voice(confirm=True)")

        return False

    print("\n🧹 RESETTING VOICE SYSTEM")

    files = [
        OWNER_WAV,
        AUTH_WAV,
        EMBED_FILE
    ]

    for file in files:

        try:

            if file.exists():

                file.unlink()

                print(f"Deleted: {file.name}")

        except Exception as e:

            print("[DELETE ERROR]", e)

    STATE["owner_embedding"] = None
    STATE["failed"] = 0
    STATE["lock_until"] = 0

    gc.collect()

    print("\n✅ RESET COMPLETE")

    return True


# ==========================================
# AUTO LOAD OWNER PROFILE
# ==========================================

STATE["owner_embedding"] = load_embedding()

# ==========================================
# PRELOAD ENGINE
# ==========================================

try:

    load_engine()

except Exception as e:

    print("[ENGINE ERROR]", e)

# ==========================================
# FIRST BOOT AUTO ENROLL
# ==========================================

if STATE["owner_embedding"] is None:

    print("\n[VOICE AUTH] No owner profile detected")
    print("[VOICE AUTH] Starting first-time enrollment")

    try:

        enroll_owner()

    except Exception as e:

        print("[ENROLL ERROR]", e)

# ==========================================
# CLI MENU
# ==========================================

if __name__ == "__main__":

    print("\n===================================")
    print("      H.E.A.R.T VOICE SECURITY")
    print("===================================")

    print("\n1. Authenticate")
    print("2. Reset Voice")
    print("3. Re-Enroll Voice")
    print("4. Exit")

    choice = input("\nSelect option: ").strip()

    # ======================================
    # AUTHENTICATE
    # ======================================

    if choice == "1":

        result = authenticate_once()

        print("\nRESULT:", result)

    # ======================================
    # RESET
    # ======================================

    elif choice == "2":

        confirm = input(
            "Type RESET to confirm: "
        ).strip()

        if confirm == "RESET":

            reset_voice(confirm=True)

        else:

            print("Cancelled")

    # ======================================
    # RE-ENROLL
    # ======================================

    elif choice == "3":

        confirm = input(
            "Type RESET to replace voice: "
        ).strip()

        if confirm == "RESET":

            reset_voice(confirm=True)

            enroll_owner()

        else:

            print("Cancelled")

    else:

        print("Exit")
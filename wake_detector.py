# =========================================
# wake.py
# HEART ULTRA-FAST WAKE SYSTEM
# OPTIMIZED + VOICE AUTH COMPATIBLE
# =========================================

import os
import json
import queue
import threading
import time

import sounddevice as sd

from vosk import Model, KaldiRecognizer

# =========================================
# CONFIG
# =========================================
MODEL_PATH = (
    r"C:\Users\Tilak Kumar\PycharmProjects"
    r"\PythonProject2\vosk-model-small-en-us-0.15"
)

SAMPLE_RATE = 16000
BLOCK_SIZE = 4000

WAKE_WORDS = [
    "wake up",
    "daddy home"
]

# =========================================
# GLOBALS
# =========================================
q = queue.Queue(maxsize=20)

heart_active = threading.Event()

model = None
recognizer = None

stream = None

# =========================================
# INIT MODEL
# =========================================
def init_model():

    global model
    global recognizer

    print("🔧 Initializing wake system...")
    print("Loading wake model...")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Wake model not found:\n{MODEL_PATH}"
        )

    model = Model(MODEL_PATH)

    recognizer = KaldiRecognizer(
        model,
        SAMPLE_RATE
    )

    recognizer.SetWords(False)

    print("✅ Wake model ready")


# =========================================
# AUDIO CALLBACK
# =========================================
def callback(indata, frames, time_info, status):

    if status:
        print(f"⚠️ Audio issue: {status}")

    try:

        q.put_nowait(bytes(indata))

    except queue.Full:
        pass


# =========================================
# CHECK WAKE WORD
# =========================================
def is_wake(text):

    text = text.lower().strip()

    return any(
        wake in text
        for wake in WAKE_WORDS
    )


# =========================================
# STOP LISTENING
# IMPORTANT FOR VOICE AUTH
# =========================================
def stop_listening():

    global stream

    try:

        if stream is not None:

            stream.stop()
            stream.close()

            stream = None

    except:
        pass

    # clear queued audio
    while not q.empty():

        try:
            q.get_nowait()
        except:
            break


# =========================================
# SINGLE-SHOT LISTEN
# IMPORTANT:
# NO INFINITE LOOP INSIDE
# =========================================
def listen():

    global recognizer
    global stream

    if recognizer is None:
        raise RuntimeError(
            "Wake model not initialized."
        )

    try:

        print("🎤 Listening for wake word...")

        # =====================================
        # OPEN MICROPHONE
        # =====================================
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=callback
        )

        stream.start()

        start_time = time.time()

        # =====================================
        # LISTEN ONLY SHORT TIME
        # =====================================
        while time.time() - start_time < 4:

            try:

                data = q.get(timeout=0.5)

            except queue.Empty:
                continue

            # =================================
            # PROCESS AUDIO
            # =================================
            if recognizer.AcceptWaveform(data):

                result = json.loads(
                    recognizer.Result()
                )

                text = result.get("text", "")

            else:

                result = json.loads(
                    recognizer.PartialResult()
                )

                text = result.get("partial", "")

            # =================================
            # PRINT SPEECH
            # =================================
            if text:

                print(f"🗣️ Heard: {text}")

            # =================================
            # WAKE DETECTED
            # =================================
            if is_wake(text):

                print("🎯 Wake word detected!")

                # VERY IMPORTANT
                # RELEASE MICROPHONE
                stop_listening()

                return True

        # timeout
        stop_listening()

        return False

    except Exception as e:

        stop_listening()

        print(f"[WAKE ERROR] {e}")

        return False


# =========================================
# TEST
# =========================================
if __name__ == "__main__":

    init_model()

    print("⌛ Waiting for wake word...")

    while True:

        heard = listen()

        if not heard:
            continue

        print("❤️ HEART ACTIVATED")

        break
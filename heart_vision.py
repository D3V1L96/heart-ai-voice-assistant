import asyncio
import threading
import time
import logging
import cv2
import pyttsx3
import speech_recognition as sr
import warnings
import os

# ====================== MAXIMUM WARNING SUPPRESSION ======================
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.simplefilter("ignore")
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*clip.*")
warnings.filterwarnings("ignore", message=".*torch.jit.load.*")
warnings.filterwarnings("ignore", message=".*hashlib.*")
# ===========================================================================

from ultralytics import YOLOWorld
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] HEART — %(message)s")
log = logging.getLogger("HEART")


class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 170)
        self.queue = asyncio.Queue()
        asyncio.create_task(self.voice_worker())

    async def speak(self, text):
        if not text: return
        print(f"\n❤️ HEART: {text}\n")
        await self.queue.put(text)

    async def voice_worker(self):
        while True:
            text = await self.queue.get()
            await asyncio.to_thread(self._speak, text)

    def _speak(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except: pass


class FrameManager:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.frame = None
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self.update_loop, daemon=True).start()

    def update_loop(self):
        log.info("📷 Camera started - Real-time open world mode")
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
            time.sleep(0.03)

    def get_frame(self):
        return self.frame.copy() if self.frame is not None else None


class HEART:
    def __init__(self):
        log.info("Loading YOLO-World Open Vocabulary Model...")
        # Extra suppression just before loading model
        warnings.filterwarnings("ignore")
        self.model = YOLOWorld("yolov8s-worldv2.pt")
        self.voice = VoiceEngine()
        self.listener = VoiceListener()
        self.frame_manager = FrameManager()
        self.last_detected = []
        self.ddgs = DDGS()

    async def start(self):
        self.frame_manager.start()
        await self.voice.speak("Heart is alive. Now seeing the real world.")
        await asyncio.sleep(1)
        await self.voice.speak("Try saying 'what do you see' or 'what is this'")

        while True:
            cmd = await self.listener.listen()
            if cmd:
                await self.process_command(cmd.lower().strip())

    # Rest of the class remains the same
    async def process_command(self, text: str):
        print(f"DEBUG - Recognized: '{text}'")

        if any(phrase in text for phrase in ["what do you see", "describe", "objects", "scene", "see"]):
            await self.see_scene()

        elif any(phrase in text for phrase in ["what is this", "what is that", "what's this", "focus", "identify", "center"]):
            await self.focus_center_object()

        elif any(phrase in text for phrase in ["tell me more", "search", "info", "about"]):
            if self.last_detected:
                await self.search_about_object(self.last_detected[0])
            else:
                await self.voice.speak("Please identify an object first.")

    async def see_scene(self):
        frame = self.frame_manager.get_frame()
        if frame is None:
            await self.voice.speak("Camera not ready.")
            return

        dynamic_classes = ["person", "object", "device", "electronics", "furniture", "bag", "bottle",
                         "cup", "book", "phone", "laptop", "monitor", "keyboard", "mouse", "headphones",
                         "plant", "chair", "table", "door", "window", "shoe", "fan", "tv"]

        self.model.set_classes(dynamic_classes)
        results = self.model(frame, conf=0.24, verbose=False)
        self.visualize(frame, results)

        detected = []
        for result in results:
            for box in result.boxes:
                label = result.names[int(box.cls)]
                if label not in ["object", "item", "thing"] and label not in detected:
                    detected.append(label)

        self.last_detected = detected

        if detected:
            await self.voice.speak(f"I can see: {', '.join(detected[:8])}")
        else:
            await self.voice.speak("Nothing clear detected right now.")

    async def focus_center_object(self):
        frame = self.frame_manager.get_frame()
        if frame is None: return

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        self.model.set_classes(["person", "object", "device", "electronics", "furniture", "bottle", "phone"])
        results = self.model(frame, conf=0.23, verbose=False)
        self.visualize(frame, results)

        best_obj = None
        best_dist = 999999

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                ox = (x1 + x2) // 2
                oy = (y1 + y2) // 2
                dist = abs(cx - ox) + abs(cy - oy)
                label = result.names[int(box.cls)]
                if dist < best_dist and label not in ["object", "item", "thing"]:
                    best_dist = dist
                    best_obj = label

        if best_obj:
            self.last_detected = [best_obj]
            await self.voice.speak(f"Focused on the {best_obj}.")
            await asyncio.sleep(0.7)
            await self.search_about_object(best_obj)
        else:
            await self.voice.speak("I can't see any clear object in the center.")

    async def search_about_object(self, obj_name: str):
        await self.voice.speak(f"Searching about {obj_name}...")
        try:
            results = list(self.ddgs.text(obj_name, max_results=3))
            if results and results[0].get('body'):
                summary = results[0]['body'][:160] + "..."
                await self.voice.speak(f"{obj_name.capitalize()}: {summary}")
            else:
                await self.voice.speak(f"Found some information about {obj_name}.")
        except:
            await self.voice.speak("Internet search is not available right now.")

    def visualize(self, frame, results):
        vis = frame.copy()
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = result.names[int(box.cls)]
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(vis, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.imshow("HEART - Real Time Vision", vis)
        cv2.waitKey(1)


class VoiceListener:
    def __init__(self):
        self.rec = sr.Recognizer()
        self.mic = sr.Microphone()
        self.rec.dynamic_energy_threshold = True
        self.rec.energy_threshold = 280

    async def listen(self):
        def callback():
            try:
                with self.mic as source:
                    print("\nYOU: ", end="", flush=True)
                    self.rec.adjust_for_ambient_noise(source, duration=0.7)
                    audio = self.rec.listen(source, timeout=8, phrase_time_limit=8)
                    text = self.rec.recognize_google(audio, language="en-IN")
                    print(text)
                    return text.strip()
            except:
                print("(listening...)")
                return ""
        return await asyncio.to_thread(callback)


async def main():
    heart = HEART()
    try:
        await heart.start()
    except KeyboardInterrupt:
        print("\n❤️ HEART stopped.")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
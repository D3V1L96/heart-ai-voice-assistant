import time
import random
import requests
import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# ====================== CONFIG ======================
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL = "llama-3.1-8b-instant"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a mature, calm, and understanding 32-year-old Indian man. 
You are wise, respectful, and emotionally intelligent. 
Reply naturally in Hinglish when it feels right. 
Keep replies short to medium (10-35 words). 
Use emojis very sparingly."""


class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.last_messages = {}
        self.last_checked = {}

    def start(self):
        print("🚀 Starting WhatsApp Bot with Brave...")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Brave Path
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in brave_paths:
            if os.path.exists(path):
                chrome_options.binary_location = path
                print(f"✅ Using Brave: {path}")
                break

        service = Service(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.get("https://web.whatsapp.com")
        print("📱 Scan QR Code...")

        for _ in range(40):
            try:
                self.driver.find_element(By.XPATH, '//div[@data-testid="chat-list"]')
                print("✅ Logged In!")
                break
            except:
                time.sleep(3)

    def get_reply(self, sender_name: str, message: str):
        prompt = f"""{SYSTEM_PROMPT}

{sender_name}: {message}

Natural reply:"""
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.85,
                      "max_tokens": 200},
                timeout=20
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()[:200]
        except Exception as e:
            logger.error(f"Groq Error: {e}")
        return "Samajh gaya, batao kya baat hai?"

    def listen_and_reply(self):
        print("🎧 Listening for new messages... (Improved Detection)")
        while True:
            try:
                # Click on chats that have unread indicator
                unread_indicators = self.driver.find_elements(By.XPATH,
                                                              '//span[contains(@aria-label, "unread") or contains(@aria-label, "messages")]')

                for indicator in unread_indicators[:5]:
                    try:
                        chat = indicator.find_element(By.XPATH, './ancestor::div[@role="listitem"]')
                        chat.click()
                        time.sleep(2.5)

                        # Get sender name
                        try:
                            sender = self.driver.find_element(By.XPATH, '//header//span[@title]').text
                        except:
                            sender = "Bhai"

                        # Get ALL incoming messages and take the last one
                        messages = self.driver.find_elements(By.XPATH,
                                                             '//div[contains(@class, "message-in")]//span[contains(@class, "selectable-text") and string-length(text()) > 1]'
                                                             )

                        if not messages:
                            continue

                        last_message = messages[-1].text.strip()

                        msg_key = f"{sender}:{last_message[-80:]}"
                        if msg_key in self.last_messages:
                            continue

                        self.last_messages[msg_key] = time.time()
                        print(f"📩 New Message from {sender}: {last_message}")

                        reply = self.get_reply(sender, last_message)
                        if reply:
                            input_box = self.driver.find_element(By.XPATH,
                                                                 '//div[@contenteditable="true" and @role="textbox"]')
                            input_box.click()
                            time.sleep(0.8)
                            input_box.send_keys(reply)
                            input_box.send_keys(Keys.ENTER)
                            print(f"❤️ Replied: {reply}")
                            time.sleep(random.uniform(2.5, 6))

                    except:
                        continue

                # Also check pinned/recent chats
                time.sleep(5)

            except Exception as e:
                logger.error(f"Loop Error: {e}")
                time.sleep(8)

    def run(self):
        try:
            self.start()
            self.listen_and_reply()
        except KeyboardInterrupt:
            print("\n🛑 Stopped.")
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    bot = WhatsAppBot()
    bot.run()
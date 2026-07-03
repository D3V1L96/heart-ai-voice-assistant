import threading
import time

class AgentSupervisor:

    def __init__(self):

        self.agent_running = False
        self.last_activity = time.time()
        self.idle_timeout = 1800  # 30 min idle restart

        self.lock = threading.Lock()

    # ---------------------
    # ACTIVITY PING
    # ---------------------
    def ping(self):

        with self.lock:

            self.last_activity = time.time()

    # ---------------------
    # IDLE CHECK
    # ---------------------
    def is_idle(self):

        return (time.time() - self.last_activity) > self.idle_timeout

    # ---------------------
    # START AGENT
    # ---------------------
    def start_agent(self, target):

        if self.agent_running:
            return

        self.agent_running = True

        def runner():

            try:
                target()
            finally:
                self.agent_running = False

        threading.Thread(target=runner, daemon=True).start()

    # ---------------------
    # SILENT RESTART
    # ---------------------
    def restart_agent(self, target):

        print("[HEART] Silent agent restart")

        self.agent_running = False

        time.sleep(2)

        self.start_agent(target)


# GLOBAL INSTANCE
agent_supervisor = AgentSupervisor()
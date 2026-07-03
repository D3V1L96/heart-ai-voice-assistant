from brain import process_command
from logger import get_logger

log = get_logger("MAIN")

def main():
    log.info("heart Assistant Started")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            log.info("heart shutting down")
            break

        log.info(f"User said: {user_input}")

        response = process_command(user_input)

        log.info(f"heart response: {response}")
        print("HEX:", response)


if __name__ == "__main__":
    main()

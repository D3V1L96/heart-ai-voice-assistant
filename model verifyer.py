import os

MODEL_PATH = r"C:\Users\Tilak Kumar\PycharmProjects\PythonProject2\vosk-model-small-en-us-0.15"

print("Checking model path...\n")

# 1. Path exists?
if not os.path.exists(MODEL_PATH):
    print("❌ Model folder NOT FOUND at path")
else:
    print("✅ Model folder exists")

    # 2. Check required files inside model
    required = ["am", "conf", "graph", "ivector"]

    missing = []
    for folder in required:
        if not os.path.exists(os.path.join(MODEL_PATH, folder)):
            missing.append(folder)

    if missing:
        print("❌ Model is INCOMPLETE")
        print("Missing parts:", missing)
    else:
        print("✅ Model structure looks valid")
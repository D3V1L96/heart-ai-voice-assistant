from heart_face.state import set_expression


def detect_emotion(text):

    text = text.lower()

    if any(word in text for word in ["love", "thanks", "good"]):
        set_expression("happy")

    elif any(word in text for word in ["sad", "hurt", "alone"]):
        set_expression("caring")

    elif any(word in text for word in ["angry", "hate"]):
        set_expression("serious")

    else:
        set_expression("idle")
current_expression = "idle"


def set_expression(expression):
    global current_expression
    current_expression = expression


def get_expression():
    return current_expression
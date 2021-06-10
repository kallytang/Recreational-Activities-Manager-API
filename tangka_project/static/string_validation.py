import constants
def is_valid_string(name: str):
    new_string = name.replace(" ", "")
    # getting rid of the dahses
    new_string = new_string.replace("-", "")
    if new_string:
        for letter in new_string:
            if not letter.isalpha() and not letter.isdigit():
                return False

        return True
    return False


def is_name_too_long(name: str):
    if len(name) > 50:
        return True
    else:
        return False



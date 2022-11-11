from __future__ import annotations

import datetime
import math
import random

import qrcode

BASE = 62

SECRET_KEY = "This is very secret."  # TODO: use .env or anything else

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


def base62_char_to_int(char: str) -> int:
    """Reverse of int_to_base62_char

    Args:
        char (str): The base62 char to turn into a python number.

    Raises:
        ValueError: If the char is not in base62 (decimals, up/low case alphabet)

    Returns:
        int: The number corresponding.
    """

    if char.isdigit():
        return ord(char) - DIGIT_OFFSET
    elif "A" <= char <= "Z":
        return ord(char) - UPPERCASE_OFFSET
    elif "a" <= char <= "z":
        return ord(char) - LOWERCASE_OFFSET
    else:
        raise ValueError("%s is not a valid character" % char)


def int_to_base62_char(integer: int) -> str:
    """Get an int number, return its form into base 62.

    Args:
        integer (int): The number (0 < x < 62)

    Raises:
        ValueError: If the number is < 0 or > 62, there is no representation in base62 (use int_to_base62)

    Returns:
        str: A single string character representing the number in base 62.
    """
    if integer < 10:
        return chr(integer + DIGIT_OFFSET)
    elif 10 <= integer <= 35:
        return chr(integer + UPPERCASE_OFFSET)
    elif 36 <= integer < 62:
        return chr(integer + LOWERCASE_OFFSET)
    else:
        raise ValueError("%d is not a valid integer in the range of base %d" % (integer, BASE))


def base62_to_int(key: str) -> int:
    """Reverse from int_to_base62.

    Args:
        key (str): The base62 string to turn into a python number.

    Returns:
        int: The number in a python type.
    """
    int_sum = 0
    reversed_key = key[::-1]
    for idx, char in enumerate(reversed_key):
        int_sum += base62_char_to_int(char) * (BASE**idx)
    return int_sum


def int_to_base62(integer: int) -> str:
    """Turn a number into its base62 form (0 is 0, 1 is 1, ..., 10 is A, 11 is B, ..., 36 is a, ..., 63 is 11)

    Args:
        integer (int): The number to transform

    Returns:
        str: A string representing the number in base62
    """
    # we won't step into the while if integer is 0
    # so we just solve for that case here
    if integer == 0:
        return "0"

    string = ""
    while integer > 0:
        remainder = integer % BASE
        string = int_to_base62_char(remainder) + string
        integer //= BASE
    return string


def text_to_bin(text: str) -> int:
    """Transforme text with ASCII chars to a decimal form.

    Args:
        text (str): The ASCII text to transform.

    Raises:
        ValueError: A ord from a char is > to 255 (8 bits).


    Returns:
        int: The number (First 8 bits is the last char, 8 next the second, etc..)
    """
    result = 0
    for letter in text:
        if ord(letter) > 255:
            raise ValueError("A char from the text is outside the possibilities.")
        result = (result << 8) + ord(letter)
    return result


def bin_to_text(bin_: int) -> str:
    """Take a number and turn it into a text within the ASCII table.

    Args:
        bin_ (int): _description_

    Returns:
        str: _description_
    """
    result = ""
    bytes = bin_.bit_length() // 8 + bool(bin_.bit_length() % 8)
    for i in range(bytes):
        result += chr((bin_ >> ((bytes - i - 1) * 8)) & 0b11111111)
    return result


def QR_encode(name: str, incr: int) -> str:
    timestamp = int(datetime.datetime.now().timestamp())

    random_nb = random.randint(1, 0xFFFF)
    sec = text_to_bin(SECRET_KEY)

    nb = ((text_to_bin(name) << 32) + timestamp << 8) + incr  # sort of twitter snowflakes
    nb *= sec % random_nb
    nb = (nb << 16) + random_nb
    code = int_to_base62(nb)

    return code


def QR_extract_infos(code: str) -> tuple[str, int, int]:
    nb = base62_to_int(code)

    public_key = nb & 0xFFFF
    nb = (nb >> 16) // (text_to_bin(SECRET_KEY) % public_key)

    name = bin_to_text(nb >> (32 + 8))
    timestamp = (nb >> 8) & 0xFFFFFFFF
    incr = nb & 0xFF

    return (name, timestamp, incr)


if __name__ == "__main__":
    for i in range(0):
        code = QR_encode("Name", i)

        qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L)
        qr.add_data(f"https://foo.bar/dive/{code}")
        img = qr.make_image()
        img.save(f"./data/results/{code}.png")

from __future__ import annotations

import datetime
import os
import random
from typing import TYPE_CHECKING

import qrcode
from dotenv import load_dotenv

if TYPE_CHECKING:
    from qrcode import BaseImage

load_dotenv()

BASE_URL = "https://digidive.schauli.com/dive/{code}"

BASE = 62

UPPERCASE_OFFSET = 55
LOWERCASE_OFFSET = 61
DIGIT_OFFSET = 48


def mask(bytes: int) -> int:
    """Make a mask with a given number of bytes.

    Example:
        mask(1) = 0b11111111
        mask(2) = 0b1111111111111111
        mask(3) = 0b111111111111111111111111

    Args:
        bytes: the number of bytes to mask.

    Returns:
        the mask
    """
    return (1 << (bytes * 8)) - 1


def get_bytes(number: int, bytes: int) -> tuple[int, int]:
    """Return the n first bytes and the rest of the number.

    Example:
        get_bytes(0b100101100110, 1) = (0b10010110, 0b110)

    Args:
        bytes: the number of bytes to get.

    Returns:
        a tuple with the rest of the number and the n first bytes.
    """
    return (number >> (bytes * 8), number & mask(bytes))


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
        raise ValueError(f"{char} is not a valid character")


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
        raise ValueError(f"{integer} is not a valid integer in the range of base {BASE}")


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


def generate_code(incr: int) -> str:
    version = 2  # 1 byte value
    timestamp = int(datetime.datetime.now().timestamp())

    random_nb = random.randint(1, 0xFFFF)  # noqa: S311

    value = timestamp  # 4 bytes
    value = (value << 8) + incr  # 1 byte

    value *= random_nb
    value = (value << 16) + random_nb  # 2 bytes

    value = (value << 8) + version  # 1 byte

    code = int_to_base62(value)

    return code


def extract_infos_from_code(code: str) -> tuple[int, int, int]:
    value = base62_to_int(code)

    value, version = get_bytes(value, 1)  # first byte

    if version == 1:
        secret_key = os.getenv("SECRET_KEY", "This is very secret.")
        secret = text_to_bin(secret_key)

        value, public_key = get_bytes(value, 2)

        value = value // (secret % public_key)

        value, incr = get_bytes(value, 1)
        timestamp = value

        return (version, timestamp, incr)
    elif version == 2:
        value, public_key = get_bytes(value, 2)

        value = value // public_key
        value, incr = get_bytes(value, 1)
        timestamp = value

        return (version, timestamp, incr)
    else:
        raise ValueError(f"Version {version} is not supported.")


def make_qr_code(code: str) -> BaseImage:
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L, border=0)
    qr.add_data(BASE_URL.format(code=code))
    img = qr.make_image()
    return img

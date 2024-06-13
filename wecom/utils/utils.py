# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""

import re
import secrets
from typing import List

from flask import flash

RANDOM_STRING_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", category)


def get_random_secret_key():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    return get_random_string(50, chars)


def get_random_string(length, allowed_chars=RANDOM_STRING_CHARS):
    """
    Return a securely generated random string.

    The bit length of the returned value can be calculated with the formula:
        log_2(len(allowed_chars)^length)

    For example, with default `allowed_chars` (26+26+10), this gives:
      * length: 12, bit length =~ 71 bits
      * length: 22, bit length =~ 131 bits
    """
    return "".join(secrets.choice(allowed_chars) for i in range(length))


def split_long_text_by_sentences(long_text: str, max_length: int = 600) -> List[str]:
    if len(long_text) < max_length:
        return [long_text]

    sentence_endings = ['\n']
    sentence_list = re.compile(r"[%s]" % "".join(sentence_endings)).split(long_text)
    print(sentence_list)

    segment = []
    fragments = []

    for sentence in sentence_list:
        if len("".join(segment)) <= max_length:
            segment.append(sentence)
            continue

        prompt_divider = segment[-1]
        if re.compile(r"={25,50}").search(prompt_divider):
            fragments.append("\n".join(segment[:-1]))
            segment.clear()
            segment.append(prompt_divider)
        else:
            fragments.append("\n".join(segment[:]))
            segment.clear()

        segment.append(sentence)

    if segment:
        fragments.append("\n".join(segment[:]))

    return fragments

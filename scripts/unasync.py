#!/usr/bin/env python3
"""Script to generate a synchronous version of the API from the asynchronous version."""

# freely inspired from https://github.com/encode/httpcore/blob/master/scripts/unasync.py
# under BSD-3-Clause license https://github.com/encode/httpcore/blob/master/LICENSE.md

from pprint import pprint
import re
import sys

SUBSTITUTIONS = [
    ("async def ", "def "),
    ("await self._async_post", "self._post"),
    ("await self._async_get", "self._get"),
    ("class AsyncEcos", "class Ecos"),
    ("Implementation of an asynchronous class", "Implementation of a synchronous class"),
    ("Asynchronous ECOS API", "Synchronous ECOS API"),
    ("the `aiohttp` library to make asynchronous HTTP", "the `requests` library to make HTTP"),
]

COMPILED_SUBSTITUTIONS = [
    (re.compile(r'(^|\b)' + regex + r'($|\b)'), repl)
    for regex, repl in SUBSTITUTIONS
]

USED_SUBSTITUTIONS = set()


def unasync_line(line):
    """Apply substitutions to a line."""
    for index, (regex, repl) in enumerate(COMPILED_SUBSTITUTIONS):
        old_line = line
        line = re.sub(regex, repl, line)
        if old_line != line:
            USED_SUBSTITUTIONS.add(index)
    return line


def unasync_file(in_path, out_path):
    """Apply substitutions to a file."""
    with open(in_path) as in_file, open(out_path, "w", newline="") as out_file: # noqa: PTH123
        for line in in_file:
            line = unasync_line(line)
            out_file.write(line)


def unasync_file_check(in_path, out_path):
    """Check substitutions to a file."""
    with open(in_path) as in_file, open(out_path) as out_file: # noqa: PTH123
        for line_nb, (in_line, out_line) in enumerate(zip(in_file.readlines(), out_file.readlines(), strict=False)):
            expected = unasync_line(in_line)
            if out_line != expected:
                print(f'L{line_nb+1}: unasync mismatch between {in_path!r} and {out_path!r}') # noqa: T201
                print(f'Async code:         {in_line!r}') # noqa: T201
                print(f'Expected sync code: {expected!r}') # noqa: T201
                print(f'Actual sync code:   {out_line!r}') # noqa: T201
                sys.exit(1)


def main(): # noqa: D103
    if '--check' in sys.argv:
        unasync_file_check("src/ecactus/async_client.py", "src/ecactus/client.py")
    else:
        unasync_file("src/ecactus/async_client.py", "src/ecactus/client.py")

    if len(USED_SUBSTITUTIONS) != len(SUBSTITUTIONS):
        unused_subs = [SUBSTITUTIONS[i] for i in range(len(SUBSTITUTIONS)) if i not in USED_SUBSTITUTIONS]

        print("These patterns were not used:") # noqa: T201
        pprint(unused_subs) # noqa: T203
        sys.exit(1)


if __name__ == '__main__':
    main()

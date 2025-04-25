#!/usr/bin/env python3

"""
Script to check if common prefix removal helps with compression.

Answer: No. It only works with gzip to a significant degree. Bzip2 and
the name tokenizer do a good job in capturing the repetition not requiring
much overhead to store the prefix. It works for gzip though, but that has
only a 32KiB window size and is thus massively helped by such things.
"""

import sys
from typing import Iterable

def find_common_prefix(lines: Iterable[str]) -> str:
    line_iter = iter(lines)
    common_prefix = next(line_iter)
    common_prefix_length = len(common_prefix)
    for line in line_iter:
        if not line.startswith(common_prefix):
            while True:
                # This trail and error approach is very inefficient but in the
                # context of read names of length 33 with thousands of entries
                # it does not matter.
                common_prefix_length -= 1
                if common_prefix_length == 0:
                    return ""
                common_prefix = common_prefix[:common_prefix_length]
                if line.startswith(common_prefix):
                    break
    return common_prefix


def main():
    file = sys.argv[1]
    with open(file, "rt") as f:
        common_prefix = find_common_prefix(f)
    common_prefix_length = len(common_prefix)
    print(f"Common prefix: {common_prefix}")
    with open(file, "rt") as fin:
        with open(file + ".no_prefix", "wt") as fout:
            for line in fin:
                fout.write(line[common_prefix_length:])

if __name__ == "__main__":
    main()

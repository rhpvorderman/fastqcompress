#!/usr/bin/env python3

"""
Script to sort and unsort a file using the sort indexes.
"""
import argparse
import array
import operator
import itertools


def block_iterator(file):
    with open(file, "rb") as f:
        lines = []
        for index, line in enumerate(f):
            lines.append(line)
            if index % 256 == 255:
                yield lines
                lines = []
        yield lines



def sort_file(file, output, index_output):
    with open(output, "wb") as out:
        with open(index_output, "wb") as index_out:
            for block in block_iterator(file):
                indexes_and_lines = list(enumerate(block))
                indexes_and_lines.sort(key=operator.itemgetter(1))
                indexes = array.array("B", (index for index, line in
                                            indexes_and_lines))
                index_out.write(indexes.tobytes())
                for index, line in indexes_and_lines:
                    out.write(line)


def unsort_file(input, input_indexes, output):
    with open(output, "wb") as out:
        with open(input_indexes, "rb") as idxf:
            for lines in block_iterator(input):
                indexes = array.array("B")
                indexes.frombytes(idxf.read(256))
                indexes_and_lines = list(zip(indexes, lines))
                indexes_and_lines.sort(key=operator.itemgetter(0))
                for index, line in indexes_and_lines:
                    out.write(line)


def main():
    parser = argparse.ArgumentParser(__doc__)
    subparsers = parser.add_subparsers()
    sort_parser = subparsers.add_parser("sort")
    sort_parser.add_argument("input")
    sort_parser.add_argument("-o", "--output")
    sort_parser.add_argument("-i", "--indexes-output")
    unsort_parser = subparsers.add_parser("unsort")
    unsort_parser.add_argument("input")
    unsort_parser.add_argument("indexes")
    unsort_parser.add_argument("-o", "--output", default="/dev/stdout")
    args = parser.parse_args()
    if hasattr(args, "indexes"):
        unsort_file(args.input, args.indexes, args.output)
        return
    if args.output is None:
        args.output = args.input + ".sorted"
    if args.indexes_output is None:
        args.indexes_output = args.output + ".indexes"
    sort_file(args.input, args.output, args.indexes_output)

if __name__ == "__main__":
    main()

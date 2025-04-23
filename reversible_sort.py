#!/usr/bin/env python3

"""
Script to sort and unsort a file using the sort indexes.
"""
import argparse
import array
import operator

def sort_file(file, output, index_output, array_type="H"):
    with open(file, "rb") as f:
        indexes_and_lines = list(enumerate(f.readlines()))
    indexes_and_lines.sort(key=operator.itemgetter(1))
    indexes = array.array(array_type, (index for index, line in indexes_and_lines))
    with open(output, "wb") as f:
        for index, line in indexes_and_lines:
            f.write(line)
    with open(index_output, "wb") as f:
        f.write(indexes.tobytes())


def unsort_file(input, input_indexes, output, array_type="H"):
    with open(input, "rb") as f:
        lines = f.readlines()
    with open(input_indexes, "rb") as f:
        # Use frombytes rather than the __init__ method as frombytes
        # will do a memory copy rather than iterating over the bytestring.
        indexes = array.array(array_type)
        indexes.frombytes(f.read())
    indexes_and_lines = list(zip(indexes, lines))
    indexes_and_lines.sort(key=operator.itemgetter(0))
    with open(output, "wb") as f:
        for index, line in indexes_and_lines:
            f.write(line)


def main():
    parser = argparse.ArgumentParser(__doc__)
    subparsers = parser.add_subparsers()
    sort_parser = subparsers.add_parser("sort")
    sort_parser.add_argument("input")
    sort_parser.add_argument("-o", "--output")
    sort_parser.add_argument("-i", "--indexes-output")
    sort_parser.add_argument("-t", "--index-array-type", default="H")
    unsort_parser = subparsers.add_parser("unsort")
    unsort_parser.add_argument("input")
    unsort_parser.add_argument("indexes")
    unsort_parser.add_argument("-o", "--output", default="/dev/stdout")
    unsort_parser.add_argument("-t", "--index-array-type", default="H")
    args = parser.parse_args()
    if hasattr(args, "indexes"):
        unsort_file(args.input, args.indexes, args.output, args.index_array_type)
        return
    if args.output is None:
        args.output = args.input + ".sorted"
    if args.indexes_output is None:
        args.indexes_output = args.output + ".indexes"
    sort_file(args.input, args.output, args.indexes_output, args.index_array_type)

if __name__ == "__main__":
    main()

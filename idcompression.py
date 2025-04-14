#!/usr/bin/env python3

import argparse
import bz2
import gzip
import lzma
from typing import Sequence, List

import dnaio


class EncodedNames:
    number_of_names: int
    data: str

    def __init__(self, names: Sequence[str]):
        self.number_of_names = len(names)
        maximum_length = max(len(name) for name in names)
        padded_names = (name.ljust(maximum_length, "\00") for name in names)
        concat_data = "".join(padded_names)
        column_data = "".join(concat_data[i::maximum_length] for i in range(maximum_length))
        self.data = column_data

    def decode(self) -> Sequence[str]:
        data = self.data
        number_of_names = self.number_of_names
        padded_names = (data[i::number_of_names] for i in range(number_of_names))
        return [name.rstrip("\00") for name in padded_names]

    def raw_data(self):
        return self.data.encode('ascii')

class EncodedColumns:
    column_data: List[EncodedNames]

    def __init__(self, names: Sequence[str]):
        self.number_of_names = len(names)
        column_lists = []
        for i, name in enumerate(names):
            columns = name.split(":")
            if len(columns) > len(column_lists):
                to_be_added = len(columns) - len(column_lists)
                for _ in range(to_be_added):
                    column_lists.append(["" for _ in range(len(names))])
            for j, column in enumerate(columns):
                column_lists[j][i] = column
        self.column_data = [EncodedNames(column) for column in column_lists]

    def decode(self):
        decoded_columns = [column.decode() for column in self.column_data]
        return [":".join(row) for row in zip(*decoded_columns)]

    def raw_data(self):
        return b"".join(c.raw_data() for c in self.column_data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sequences", help="FASTQ or uBAM file")
    parser.add_argument("-b", "--block-size", type=int, default=10_000)
    parser.add_argument("-e", "--encoder", default="names")
    args = parser.parse_args()
    encoder = {"names": EncodedNames, "columns": EncodedColumns}[args.encoder]
    with dnaio.open(args.sequences) as seq_file:
        ids = [
            record.id for record, counter in zip(seq_file, range(args.block_size))
        ]
    encoded_ids = encoder(ids)
    concat_ids = ''.join(ids)
    assert ids == encoded_ids.decode()
    print("original length\t\t", len(concat_ids))
    print("gzipped original\t", len(gzip.compress(concat_ids.encode('ascii'))))
    print("gzipped transformed\t", len(gzip.compress(encoded_ids.raw_data())))

    print("bzipped original\t", len(bz2.compress(concat_ids.encode('ascii'))))
    print("bzipped transformed\t", len(bz2.compress(encoded_ids.raw_data())))

    print("lzma original\t\t", len(lzma.compress(concat_ids.encode('ascii'))))
    print("lzma transformed\t", len(lzma.compress(encoded_ids.raw_data())))


if __name__ == "__main__":
    main()
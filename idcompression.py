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

class EncodedColumns(EncodedNames):
    column_data: List[EncodedNames]

    def __init__(self, names: Sequence[str]):
        self.number_of_names = len(names)
        column_maxes = []
        for name in names:
            columns = name.split(":")
            if len(columns) > len(column_maxes):
                column_maxes.extend([0 for _ in range(len(columns) - len(column_maxes))])
            for i, column in enumerate(columns):
                column_maxes[i] = max(len(column), column_maxes[i])
        new_names = []
        for name in names:
            columns = name.split(":")
            for i, column in enumerate(columns):
                columns[i] = column.ljust(column_maxes[i], "\00")
            new_names.append(":".join(columns))
        super().__init__(new_names)

    def decode(self):
        decoded_data = super().decode()
        answer_names = []
        for name in decoded_data:
            answer_names.append(
                ":".join(column.rstrip("\00") for column in name.split(":"))
            )
        return answer_names


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
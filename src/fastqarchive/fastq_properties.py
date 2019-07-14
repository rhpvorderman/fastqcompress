# Copyright (C) 2019 Ruben Vorderman, Leiden University Medical Center
# This file is part of fastqarchive
#
# fastqarchive is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# fastqarchive is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with fastqarchive.  If not, see <https://www.gnu.org/licenses/

from pathlib import Path
import typing
from typing import Dict, Iterator, Tuple

import dnaio

import xopen


def count_base_and_quality_combinations(
        fastq: Path) -> Dict[Tuple[str, str], int]:
    """
    Counts base and quality combinations.
    :param fastq: The fastq file.
    :return: A dictionary {(Base, Quality): Count}
    """
    counts_dict = {}  # type: Dict[Tuple[str, str], int]

    with xopen.xopen(fastq, mode='rb') as fastq_handle:
        fastq_reader = dnaio.FastqReader(fastq_handle)
        for record in fastq_reader:  # type: dnaio.Sequence
            for base_qual_combo in zip(record.sequence, record.qualities):
                try:
                    counts_dict[base_qual_combo] += 1
                except KeyError:
                    counts_dict[base_qual_combo] = 1
    return counts_dict


# Marcelm's dnaio is slightly faster. But this algorithm comes close, without
# using cython. This is because this returns a tuple which can be unpacked,
# which is more efficient than an object with access methods.
# This can be further improved by using Cython to leverage "get line" functions
# from glibc.
def fastq_iterator(fastq_handle: typing.BinaryIO, two_headers: bool = False
                   ) -> Iterator[Tuple[bytes, bytes, bytes]]:
    """
    Iterate over fastq records return name, sequence, qualities as bytes.
    :param fastq_handle: a fastq file handle.
    :param two_headers: Whether the iterator should check if the headers are
    the same.
    :return: name, sequences, qualities. All bytestrings
    """
    while True:
        try:
            name = next(fastq_handle).rstrip()
        except StopIteration:
            return
        try:
            sequence = next(fastq_handle).rstrip()
            plus_line = next(fastq_handle)
            qualities = next(fastq_handle).rstrip()
        except StopIteration:
            raise ValueError("Incomplete Fastq Record at end of file")

        if two_headers:
            if not plus_line.rstrip()[1:] == name[1:]:
                raise ValueError(
                    "Fastq record with unequal headers: '{0}' and '{1}'"
                    "".format(name, plus_line.rstrip()))

        if len(sequence) != len(qualities):
            raise ValueError(
                "Fastq record with sequence and qualities of unequal length"
            )
        yield name, sequence, qualities

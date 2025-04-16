# fastqcompress
A repository looking at ways to compress sequencing data

This is an exploratory project for a bit of fun and hopefully some useful
findings. 

## Introduction

Sequencing data is plentiful and filesizes are typically large. Sequencing
data typically comes in formats where each data point consists of four major 
elements
- An identifier or "name". Some sequencers (i.e. Illumina) store metadata
  such as the sequencing machine ID, lane ID etc. in this field. Nanopore
  and PacBio sequencers use a random uuid.
- A sequence consisting of A, C, G, T and N bases.
- A sequence quality string that is Phred encoded with values ranging from
  0 to 93, though typically, the higher values are not used.
- Other metadata
  - Methylation information
  - Readgroup information
  - etc.

The human genome is 3 billion base pairs and in order to call variants a 
coverage of roughly 30X is desirable, meaning that most whole genome sequencing
sets contain 90 billion encoded base pairs and the same number of quality 
values leading to at least 180 billion bytes that need to be stored.
Generic compression algorithms can help somewhat but do not typically 
compress enough.

## CRAM

CRAM is a compression format for aligned data. It uses the alignment 
information to store only the part of DNA sequences that are distinct from
the reference. This allows for immense compression. It also uses some clever
codecs to store the other data. These codecs can be found 
[here](https://samtools.github.io/hts-specs/CRAMcodecs.pdf).

CRAM can achieve very high compression rates and the codecs are very good, so
this means it is extra challenging to find ideas that work better. 

## Do not compress records, compress blocks

Compressing individual records is very bad from a compression standpoint. 
Generic compression algorithms such as deflate (gzip uses this), bzip2 and lzma 
(xz uses this) look for patterns and repeats. Having a per-record format
which intermingles IDs, sequences, qualities and metadata together makes
finding patterns and repeats harder.

What CRAM does is store sequencing information in blocks. Take an x amount
of records and store all the names in one block, all the sequencing data in
another etc. 

This allows for better compression.

## Compressing sequences
Using the reference/assembly to compress your original data is by far the 
best way of doing it. For unaligned sequences some interesting tricks might
be possible.

## Compressing identifiers
CRAM tokenizes the name and stores the data in column format. This will 
work well for UUID names as these contain a few dashes at fixed intervals. 
The same is true for Illumina data with columns.

I am interested to see if we can take this further: store every character
in a single column. 

Identifiers typically contain some pattern and are usually the same length. 
Lengths are not very disparate. Let's take a look at an example from the
CRAM codecs:

```
I17_08765:2:123:61541:01763#9
I17_08765:2:123:1636:08611#9
I17_08765:2:124:45613:16161#9
```
We can tokenize this and store the separate columns, but my assumption is that
not tokenizing it and instead store every position in its own column will lead
to data that is very easy to compress with generic compression algorithm
If we store 10 000 sequences, gzip has to compress 10000 times `I` in a row.
Gzip is very efficient it this sort of thing.

For UUIDs the data looks like this:
``` 
eb588d1a-f169-47c0-8424-e9d5818c1be1
64628793-a17f-4c11-9800-c3f3952b203b
6d0f61d5-e484-41bd-a999-238fa9b2961a
c45f7008-5538-413a-b036-acd1633df21f
926b21a9-a5bc-4177-9e91-4ce52553374e
b862865e-47d4-40a0-8a3f-954206e246ff
66f5eb89-ffbc-42a5-9c01-754c6db5f2b7
4d44efb4-89ff-482c-b23a-a6698e6723c8
56a5a062-5c12-4243-8ed7-38bfb8c65ab8
5511f34a-3b81-4178-ae8e-84b60ef05ea8
```
Due to the random nature this data is hard to compress, but the dashes and the
4 are not random. Since all the IDs are the same length, the column 
transformation will work well here:

```
e66c9b6455
b4d4286d65
560566f4a1
82ffb25451
886728eeaf
d71016bf03
19d0a58b64
a3589e942a
----------
fae5a4f853
114557f9cb
6783bdbf18
9f48c4cf21
----------
4444444444
7c11102821
c1b37aa247
01da705c38
----------
89ab989b8a
4890eac2ee
20939303d8
40961f1a7e
----------
ec2a497a38
933cc55684
df8de446bb
53f152c9f6
89a62068b0
159356de8e
82b35eb6cf
cb2d325760
129f34f255
b0627623ae
e3114fbcba
1bafef7888
```
Imagine now that 10 000 sequences are stored and how well some of these
columns compress.
Will it work better than the tokenizer? It has less overhead for sure as
only max length and number of sequences need to be stored. It also works
very well with increasing identifiers as one of the columns will be 012345679
repeats, one of them repeats of 10 times 0, 10 times 1 etc. These are also
easy to compress. If the number is semi-random, and also random in length
I expect the tokenizer to perform much better.

Note that if the length of the IDs is not too variable, we can only store
the maximum length and simply add null bytes to as padding to shorter sequences.
If we have 10000 names, with almost all having a length of 50 and one of 
length 60, this means 10 columns of 9999 zeroes and one distinct character 
are formed. These are very easy to compress.

## Name transformation compression results

For the comparison we use [idcompression.py](./idcompression.py). 

### Nanopore UUID4 ID compression

A [UUID4](https://en.wikipedia.org/wiki/Universally_unique_identifier#Version_4_(random)) 
entry is a 36-byte string that looks like this:

``` 
xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
```
M is the version field, so it is always a `4`. The `N`'s upper two or three bits
encode the variant. Most UUID4s are variant 1 so that is two bits. 
The `x` are all hexadecimal numbers. So these encode for 4 bits.
The number of random bits in a UUID (assuming variant 1) is 122. This is
15.25 bytes. It takes 36 bytes to spell it out, so the theoretical best
compression removing all redundancy is 15.25 / 36 = 42.36%.

The results on 10 000 UUIDs:
``` 
original length          360000
gzipped original         204918
gzipped transformed      177194
bzipped original         183326
bzipped transformed      156585
lzma original            178036
lzma transformed         159816
```
The original is simply all the UUIDs together back to back. It turns out 
that the bzip2 result using the transformation is the best. It is just 2.67%
larger than the absolute minimum of 152500 bytes that we can obtain if we had
used a dedicated system that just stored the 122 bits that mattered.

The tokeniser in CRAM does not perform well on the same data. It
compresses it to 242453 bits that do not compress well using gzip, bzip2 or xz.

### Illumina results

``` 
original length          384576
gzipped original         59444
gzipped transformed      46675
bzipped original         47164
bzipped transformed      43690
lzma original            39748
lzma transformed         40260
```
The transformation has significant improvements, except for lzma, which is 
apparently able to handle the pattern.

The CRAM tokenizer is however much more effective getting it down to 
23080 bytes. This is due to the variable length of some of the fields which
messes up the repitition. The tokenizer handles this much better.

### Htscodecs discussion

I discussed this with JK Bonfield, the CRAM maintainer, and he showed that
the rANS4x16 can do striping and bitpacking. The striping feature is basically
doing the above transformation. As a result the rANS4x16 encoder can basically
process the UUID as four streams of only dashes one stream of only a 4, one
stream of only 8,9,A,B values (2 bits of info) and 30 streams of hexadecimals
(4bits of info). It can automatically convert those and get very close to 
only 122 bits needed per UUID.

So this can improve CRAM without adding additional codecs.

## Compressing qualities
CRAM uses the FQZComp. This codec uses some clever tricks and seems very good. 

ONT CRAM files however are unseemingly big. Most of this data is in qualities.
Let's see what kind of tricks can be leveraged.

I used a set from the s3://ont-open-data archive:

```commandline
aws s3 cp --no-sign-request s3://ont-open-data/giab_2025.01/analysis/wf-human-variation/hac/HG002/PAW70337/output/SAMPLE.haplotagged.cram HG002.cram
samtools view HG002.cram | cut -f 11 | head -n 100 > 100nanoporequals.txt
```

Let's do some investigations.
```
$ python3 -c "data = open('100nanoporequals.txt').read();print(set(data));print(len(set(data)))"
{'I', 'F', ',', '3', '8', '+', '5', '"', '@', '1', 'R', 'N', ':', '<', '?', '&', 'L', 'K', 'Q', '>', 'P', '.', '*', 'S', 'G', '6', 'A', '4', '(', '/', '$', 'H', 'E', "'", '\n', 'M', 'O', '7', '2', ';', '%', 'B', '-', '9', 'D', '#', 'C', 'J', '0', ')', '='}
51
```
51 distinct characters (including newlines) so 50 distinct phreds. That requires
5.6439 bits to encode so the ratio should be 70%ish if the data is truly random.

``` 
$ wc -c 100nanoporequals.txt 
3124721 100nanoporequals.txt
$ gzip -c 100nanoporequals.txt | wc -c
1917880
$ bzip2 -c 100nanoporequals.txt | wc -c
1751296
$ xz -c 100nanoporequals.txt | wc -c
1769008
$ ~/projects/htscodecs/tests/fqzcomp_qual 100nanoporequals.txt | wc -c
nlines=100
Total output = 1708902
1708902
```
So the fqzcomp codec is clearly the best, beating bzip2 slightly. It compresses
data to 54.7%. Not too shabby.

Is it possible to do better? 
Having a look at the phred scores

Code [here](./qual_score_counter.py). The frequencies do not suggest very 
compressible data, which is what we see in practice.

So given the ONT jitter, values hover around a certain point. What if we 
use the differences between phreds. Will that yield more compressible data?

Code [here](./qual_diff_encoder.py), answer: no.

What if we take a fixed point and only encode differences from that point
onwards. If we have a range (min, max) where min and max are at most
15 units apart, the differences can be stored 4-bit in the range.

Since phred values are ASCII they only use 7 bits. When the signal is 
erratic and the differences are great, the phreds can be stored verbatim.
When there are small differences, a range can be determined to encode. 
The range starts with the minimum value in the least significant bits 
and has the most significant bit set to signify that the encoding starts. 
The following single byte value indicates the length of the encoded stretch
from 1 to 256. (Stored as length - 1). Then follows the 4-bit offsets from
the minimum in a range of 0 to 15. 

Using the code [here](./qual_range_finder.py) we can check beforehand if this
idea has some merit.
```
Result: 
3124721
2078701
```
So definitely not as good as FQZComp, but we have not compressed the data yet.
Maybe the data is more compressible in this representation?

Tried it [in C](./diffcompress.c) and this does not work as well as planned. 
The output size is roughly as predicted, but hardly compressible at all. 
There are probably bugs in the implementation, but it is not worth pursuing it
further.
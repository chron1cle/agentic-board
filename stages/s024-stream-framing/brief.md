Implement frames.py. Input on stdin is binary: each record starts with a
four-byte unsigned big-endian length, followed by that many UTF-8 bytes.
Lengths from 0 through 65536 are valid. Print a JSON string plus newline per
complete record, including an empty string for a zero-length record, and
flush each line before reading another record. EOF between records succeeds.
Truncated length or body, excessive length, or invalid UTF-8 exits 2 without
printing the bad record. Previously complete records remain printed.
Use standard library only. The stream may be larger than memory, and a producer
may wait for a line before sending the next record.

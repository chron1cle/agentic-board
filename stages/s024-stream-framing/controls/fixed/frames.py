import json
import sys

def main():
    source = sys.stdin.buffer
    while True:
        header = source.read(4)
        if not header:
            return 0
        if len(header) != 4:
            return 2
        size = int.from_bytes(header, "big")
        if size > 65536:
            return 2
        data = source.read(size)
        if len(data) != size:
            return 2
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return 2
        print(json.dumps(text), flush=True)

if __name__ == "__main__":
    sys.exit(main())

from aggregate import report
def answer(request):
    return report(request["records"], request["keys"])


if __name__ == "__main__":
    import json
    import sys

    for line in sys.stdin:
        print(json.dumps(answer(json.loads(line))))

from functools import lru_cache
import json
import sys


def solve(case):
    labels = case["labels"]
    moves = case["moves"]
    def done(belief):
        return all(case["safe"][s] and labels[s] == labels[belief[0][0]] for s, _, _ in belief)

    def successors(belief, j):
        branches = [{} for _ in range(case["signals"])]
        for state, errors, credit in belief:
            if not moves[state][j]:
                return None
            for real, following, charge in moves[state][j]:
                if charge > credit:
                    return None
                for reported, group in enumerate(branches):
                    left = errors - (reported != real)
                    if left >= 0:
                        key = (following, left)
                        group[key] = min(group.get(key, credit), credit-charge)
        return [tuple(sorted((s, e, c) for (s, e), c in g.items())) for g in branches if g]

    @lru_cache(None)
    def wins(belief):
        if done(belief):
            return True
        return any(winning_probe(belief, j) for j in range(len(moves[0])))

    def winning_probe(belief, j):
        branches = successors(belief, j)
        return branches is not None and all(wins(branch) for branch in branches)

    result = []
    for start in case["starts"]:
        outcome = None
        for credit in range(case["cap"]+1):
            belief = tuple(sorted((s, case["errors"], credit) for s in start))
            if wins(belief):
                first = [] if done(belief) else [j for j in range(len(moves[0])) if winning_probe(belief, j)]
                outcome = dict(credit=credit, probes=first)
                break
        result.append(outcome)
    return result


if __name__ == "__main__":
    for line in sys.stdin:
        print(json.dumps(solve(json.loads(line))))

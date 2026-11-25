"""Shortest route through the graph of (node, switch mask) states."""

import heapq
import json
import sys


def minimum_cost(case):
    graph = [[] for _ in range(case["nodes"])]
    for edge in case["edges"]:
        graph[edge["u"]].append(edge)
    goal_mask = sum(1 << bit for bit in case.get("goal_on", []))
    required = sum(1 << bit for bit in case.get("arrival_on", []))
    start = (case["start"], 0)
    distances = {start: 0}
    pending = [(0, *start)]
    while pending:
        distance, node, mask = heapq.heappop(pending)
        if distance != distances[node, mask]:
            continue
        if node == case["goal"] and mask & required == required and ("goal_on" not in case or mask == goal_mask):
            return distance
        for edge in graph[node]:
            if "need_on" in edge and not mask & (1 << edge["need_on"]):
                continue
            if "need_off" in edge and mask & (1 << edge["need_off"]):
                continue
            toll = edge["cost"]
            if "on_discount" in edge:
                switch, amount = edge["on_discount"]
                if mask & (1 << switch):
                    toll -= amount
            if "off_discount" in edge:
                switch, amount = edge["off_discount"]
                if not mask & (1 << switch):
                    toll -= amount
            outgoing = mask
            if "toggle" in edge:
                outgoing ^= 1 << edge["toggle"]
            if "clear" in edge:
                outgoing &= ~(1 << edge["clear"])
            if "set" in edge:
                outgoing |= 1 << edge["set"]
            if "copy" in edge:
                source, target = edge["copy"]
                value = (outgoing >> source) & 1
                outgoing &= ~(1 << target)
                outgoing |= value << target
            next_state = (edge["v"], outgoing)
            candidate = distance + max(0, toll)
            if candidate < distances.get(next_state, float("inf")):
                distances[next_state] = candidate
                heapq.heappush(pending, (candidate, *next_state))
    return None


if __name__ == "__main__":
    for line in sys.stdin:
        print(json.dumps(minimum_cost(json.loads(line))))

import argparse
import json
import os
import random
import time
from collections import Counter
from typing import List, Dict

import ray

VOCAB = [
    "sensor", "imu", "gps", "telemetry", "packet", "error", "warning", "ok",
    "timeout", "retry", "connect", "disconnect", "motor", "servo", "altitude",
    "pressure", "temperature", "voltage", "current", "checksum", "crc",
    "calibration", "startup", "shutdown", "heartbeat", "status", "link",
    "lora", "spi", "i2c", "uart", "nav", "attitude", "quaternion", "timestamp"
]
NOISE = ["user", "system", "daemon", "kernel", "task", "thread", "buffer", "queue"]

def generate_log_lines(num_lines: int, seed: int = 42) -> List[str]:
    random.seed(seed)
    lines = []
    for i in range(num_lines):
        level = random.choice(["INFO", "WARN", "ERROR", "DEBUG"])
        tokens = []
        for _ in range(random.randint(6, 14)):
            w = random.choice(VOCAB + VOCAB + NOISE)  # weighted
            tokens.append(w)
        lines.append(f"{level} event={i} " + " ".join(tokens))
    return lines

def write_dataset(path: str, num_lines: int):
    lines = generate_log_lines(num_lines)
    with open(path, "w") as f:
        for line in lines:
            f.write(line + "\n")

def read_dataset(path: str) -> List[str]:
    with open(path, "r") as f:
        return [ln.strip() for ln in f if ln.strip()]

def chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def tokenize(line: str) -> List[str]:
    parts = line.lower().split()
    out = []
    for p in parts:
        if p.startswith("event="):
            out.append("event")
        else:
            out.append(p)
    return out

@ray.remote
def count_chunk(lines: List[str]) -> Dict[str, int]:
    c = Counter()
    for line in lines:
        c.update(tokenize(line))
    return dict(c)

def merge_counts(dicts: List[Dict[str, int]]) -> Counter:
    total = Counter()
    for d in dicts:
        total.update(d)
    return total

def main():
    parser = argparse.ArgumentParser(description="Ray distributed log analytics")
    parser.add_argument("--dataset", default="telemetry_logs.txt")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--lines", type=int, default=30000)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    if args.generate or not os.path.exists(args.dataset):
        print(f"[HEAD] Generating dataset: {args.dataset} ({args.lines} lines)")
        write_dataset(args.dataset, args.lines)

    print(f"[HEAD] Reading dataset: {args.dataset}")
    lines = read_dataset(args.dataset)
    chunks = chunk_list(lines, args.chunk_size)

    print(f"[HEAD] Total lines: {len(lines)}")
    print(f"[HEAD] Chunk size: {args.chunk_size}")
    print(f"[HEAD] Total tasks: {len(chunks)}")

    ray.init(address="auto")

    start = time.time()

    futures = [count_chunk.remote(ch) for ch in chunks]
    partials = ray.get(futures)

    total = merge_counts(partials)

    elapsed = time.time() - start

    top_items = total.most_common(args.top)

    print("\n[RESULT] Top tokens")
    for tok, cnt in top_items:
        print(f"{tok:15s} {cnt}")

    print(f"\n[RESULT] Distributed analysis time: {elapsed:.2f}s")

    out = {
        "dataset": args.dataset,
        "lines": len(lines),
        "chunk_size": args.chunk_size,
        "tasks": len(chunks),
        "top": top_items,
        "elapsed_s": round(elapsed, 2),
        "full_counts": dict(total),
    }

    with open("final_wordcount.json", "w") as f:
        json.dump(out, f, indent=2)

    print("[RESULT] Wrote final_wordcount.json")

if __name__ == "__main__":
    main()

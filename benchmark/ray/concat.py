import ray
import time
import json

@ray.remote
def generate(size: int):
    return [i for i in range(size)]

@ray.remote
def merge(left: list, right: list):
    return left + right

with open("input", "r") as f:
    matrix_size, matrix_num = map(int, f.readline().split())

with open("result.json", "r") as f:
    data = json.load(f)
    start = time.time()
    results = []
    for i in range(matrix_num):
        results.append(generate.remote(matrix_size))
    for i in range(1, matrix_num):
        results[0] = merge.remote(results[0], results[i])
    ray.get(results[0])
    end = time.time()
    key = f"matrix_num={matrix_num},cluster_num=2"
    if key not in data:
        data[key] = []
    data[key].append((matrix_size, end-start))

with open("result.json", "w") as f:
    json.dump(data, f, indent=2)


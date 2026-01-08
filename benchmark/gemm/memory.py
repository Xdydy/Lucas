import matplotlib.pyplot as plt
import numpy as np


start_t = None
x1 = []
y1 = []
x2 = []
y2 = []
with open("memory_baseline.dat", 'r') as f:
    lines = f.readlines()
    for line in lines:
        if line.startswith("MEM"):
            title, mem, t = line.split()
            mem = float(mem)
            t = float(t)
            if start_t is None:
                start_t = t
            x1.append(t - start_t)
            y1.append(mem)

start_t = None
with open("memory_ad.dat", "r") as f:
    lines = f.readlines()
    for line in lines:
        if line.startswith("MEM"):
            title, mem, t = line.split()
            mem = float(mem)
            t = float(t)
            if start_t is None:
                start_t = t
            x2.append(t-start_t)
            y2.append(mem)

plt.figure(figsize=(12, 6)) 
plt.plot(x1, y1, color='r', label='Seq Execution')
plt.fill_between(x1, y1, color='r', alpha=0.3)
plt.plot(x2, y2, color='g', label='DAG Execution')
plt.fill_between(x2, y2, color='g', alpha=0.3)
plt.title('Memory Usage of GEMM (matrix_size=1024x1024)')
plt.xlabel('Time (s)')
plt.ylabel('Memory Usage (MB)')
plt.legend()
plt.savefig('memory.png')
plt.close()


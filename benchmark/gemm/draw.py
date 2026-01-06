import matplotlib.pyplot as plt
import numpy as np
import math
import json

base = None
parallel = None
with open("result.json", 'r') as f:
    data = json.load(f)
    base = data['base']
    parallel = data['ad']

fig, axes = plt.subplots(1,2, figsize=(12, 6), sharey=True)
letters = ['a', 'b']
for i in range(2):
    ax = axes[i]
    matrix_size = '1024' if i == 0 else '2048'
    x = []
    y1 = []
    y2 = []
    base_data = base['matrix_size']
    para_data = parallel['matrix_size']
    for item in base_data[matrix_size]:
        x.append(f"{int(matrix_size)//int(item[0])}")
        y1.append(item[1])
    for item in para_data[matrix_size]:
        y2.append(item[1])
    # 取对数
    x = x[::-1]
    x = [math.log(int(item), 2) for item in x]
    y1 = np.log(y1)
    y2 = np.log(y2)
    y1 = y1[::-1]
    y2 = y2[::-1]
    ax.plot(x, y1, marker='o', color='r', label='Seq Execution')
    ax.plot(x, y2, marker='s', color='g', label='DAG Execution')
    ax.set_title(f'({letters[i]}) matrix_size={matrix_size}x{matrix_size}')
    ax.set_xlabel(f'Matrix\'s Parallelism $(2^x)$')
    ax.legend()
# 添加标题和标签
axes[0].set_ylabel('Latency (log scale)')
plt.suptitle('Gemm\'s Latency of Different Matrix Size and Matrix Batch Size')
fig.savefig('gemm1.png')
plt.close()

x = []
y1 = []
y2 = []
para_1024 = parallel['matrix_size']['1024']
para_2048 = parallel['matrix_size']['2048']
for item in para_1024:
    x.append(f"{int(matrix_size)//int(item[0])}")
    y1.append(item[1])
for item in para_2048:
    y2.append(item[1])
# 取对数
y1 = np.log(y1)
y2 = np.log(y2)
x = x[::-1]
x = [math.log(int(item), 2) for item in x]
y1 = y1[::-1]
y2 = y2[::-1]
plt.plot(x, y1, marker='o', color='r', label='1024x1024')
plt.plot(x, y2, marker='s', color='g', label='2048x2048')
plt.title('Gemm\'s Latency of Different Matrix Size and Matrix Batch Size')
plt.xlabel('Matrix\'s Parallelism $(2^x)$')
plt.ylabel('Latency (log scale)')
plt.legend()
plt.savefig('gemm2.png')
plt.close()

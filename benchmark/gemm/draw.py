import matplotlib.pyplot as plt
import numpy as np
import json

categories = []
for size in [1,2,4,8,16]:
    categories.append(size*size)
base = None
parallel = None
with open("result.json", 'r') as f:
    data = json.load(f)
    base = data['base']
    parallel = data['ad']
m_256_base = []
m_256_parallel = []
m_512_base = []
m_512_parallel = []
for key, value in base.items():
    key: str
    if key.startswith("256x"):
        m_256_base.append(value)
    if key.startswith("512x"):
        m_512_base.append(value)
for key, value in parallel.items():
    key: str
    if key.startswith("256x"):
        m_256_parallel.append(value)
    if key.startswith("512x"):
        m_512_parallel.append(value)
# 定义数据
x = np.arange(len(categories))
# 绘制柱状图
plt.subplot(1,1,1)
plt.plot(x, m_256_base, marker='o', color='r', label='Matrix Size 1024x1024 with Seq Execution')
plt.plot(x, m_256_parallel, marker='s', color='g', label='Matrix Size 1024x1024 with DAG Execution')
plt.plot(x, m_512_base, marker='^', color='b', label='Matrix Size 2048x2048 with Seq Execution')
plt.plot(x, m_512_parallel, marker='x', color='y', label='Matrix Size 2048x2048 with DAG Execution')


# 添加标题和标签
plt.title('Gemm\'s Latency of Different Matrix Size and Matrix Split Num')
plt.xlabel('Matrix\'s Split Num')
plt.ylabel('Latency (s)')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('draw.png')
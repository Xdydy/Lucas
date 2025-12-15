import matplotlib.pyplot as plt
import numpy as np
with open("dag.txt", "r") as f:
    lines = f.readlines()
# 定义数据
categories = []
values = [] # baseline
for line in lines:
    parts = line.strip().split()
    categories.append(parts[0])
    values.append(float(parts[1]))

bar_width = 0.35
x = np.arange(len(categories))
# 绘制柱状图
plt.bar(x , values, width=bar_width, color='b', label='DAG generation time')

# 添加标题和标签
plt.title('DAG Generation Latency of Different Nodes')
plt.xlabel('DAG\'s size')
plt.ylabel('Latency')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('bar.png')
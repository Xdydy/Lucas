import matplotlib.pyplot as plt
import numpy as np
# 定义数据
with open("base.txt", "r") as f:
    lines = f.readlines()
values_base = [float(line.strip().split()[-1]) for line in lines]
with open("path.txt", "r") as f:
    lines = f.readlines()
values_path = [float(line.strip().split()[-1]) for line in lines]
categories = ['1000kb','2000kb','3000kb','4000kb']
bar_width = 0.25
x = np.arange(len(categories))
# 绘制柱状图
# plt.bar(x - bar_width , values1, width=bar_width, color='r', label='baseline')
# plt.bar(x, values3, width=bar_width, color='g', label='static workflow with eager')
# plt.bar(x + bar_width, values2, width=bar_width, color='b', label='lucas workflow')

plt.plot(x, values_base, marker='o', color='r', label='Robin')
plt.plot(x, values_path, marker='s', color='g', label='Key Path')

# 添加标题和标签
plt.title('Key Path\'s Latency of Different Workloads')
plt.xlabel('Data\'s size')
plt.ylabel('Latency (s)')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('draw.png')
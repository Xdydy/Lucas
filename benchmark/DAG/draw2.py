import matplotlib.pyplot as plt
import numpy as np
with open("dag.txt", "r") as f:
    lines = f.readlines()
# 定义数据
labels = []
dag_generation_times = [] # baseline
dag_execute_times = []
for line in lines:
    parts = line.strip().split()
    labels.append(parts[0])
    dag_generation_times.append(float(parts[1]))
    dag_execute_times.append(float(parts[2]))

bar_width = 0.35
x = np.arange(len(labels))
# 绘制柱状图
plt.bar(x , dag_generation_times, width=bar_width, color='b', label='DAG generation time')
plt.bar(x , dag_execute_times, width=bar_width, bottom=dag_generation_times, color='r', label='DAG execution time')

# 添加标题和标签
plt.title('Workflow Latency of Different Nodes')
plt.xlabel('DAG\'s size')
plt.ylabel('Latency')

plt.xticks(x, labels)
plt.legend()

# 显示图形
plt.savefig('workflow.png')
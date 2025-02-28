import matplotlib.pyplot as plt
import numpy as np
# 定义数据
categories = ['10MB','20MB','50MB','100MB']
values_dDAG = [17.23,   26.45,  29.89,   46.82] # data_size=100Mb
# values_psDAG = [6.94,   11.56,   14.68,   29.82] # static with eager
values_psDAG = [16.52,   19.52,   20.09,   31.23] # static with eager
values_lDAG = [7.8,    11.52,   12.20,   27.32] # data_size=100Mb
bar_width = 0.25
x = np.arange(len(categories))
# 绘制柱状图
# plt.bar(x - bar_width , values1, width=bar_width, color='r', label='baseline')
# plt.bar(x, values3, width=bar_width, color='g', label='static workflow with eager')
# plt.bar(x + bar_width, values2, width=bar_width, color='b', label='lucas workflow')

plt.plot(x, values_dDAG, marker='o', color='r', label='baseline')
plt.plot(x, values_psDAG, marker='s', color='g', label='static workflow with eager')
plt.plot(x, values_lDAG, marker='^', color='b', label='lucas workflow')

# 添加标题和标签
plt.title('WordCount\'s Latecy of Different Workloads')
plt.xlabel('Data\'s size')
plt.ylabel('Latecy (s)')

plt.xticks(x, categories)
plt.legend()

# 显示图形
plt.savefig('big_data.png')
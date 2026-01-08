import matplotlib.pyplot as plt
import math
import numpy as np
import json

base = None
adv = None
with open("result.json", "r") as f:
    data = json.load(f)
    base = data["base"]
    adv = data["path"]

letters = ["a", "b", "c"]
fig, axs = plt.subplots(1, 3,figsize=(16, 6), sharey=True)
for i in range(2,5):
    x1 = []
    y1_base = []
    y1_adv = []
    key = f"matrix_size=100000,cluster_num={i}"
    diff = []
    y_base = None
    y_adv = None
    for item in base[key]:
        x1.append(item[0])
        y1_base.append(item[1])
        y_base = item[1]
    for item in adv[key]:
        y1_adv.append(item[1])
        y_adv = item[1]
    diff.append(1 - y_adv / y_base)
    axs[i-2].plot(x1, y1_base, marker="o", color="blue", label="Robin Scheduler")
    axs[i-2].plot(x1, y1_adv, marker="x", color="red", label="KeyPath Scheduler")
    axs[i-2].legend()
    axs[i-2].set_title(f"({letters[i-2]}) matrix_size=100000,cluster_num={i}")
    axs[i-2].set_xlabel(f"matrix_num")
    print(f"diff_avg={np.mean(diff)}")
axs[0].set_ylabel("Latency (s)")
plt.suptitle("Concat's Latency of Different Matrix Number and Cluster Number", fontsize=16)
fig.savefig("concat1.png")
plt.close()

fig, axs = plt.subplots(1, 3,figsize=(16, 6), sharey=True)
for i in range(2,5):
    x1 = []
    y1_base = []
    y1_adv = []
    key = f"matrix_num=20,cluster_num={i}"
    diff = []
    y_base = None
    y_adv = None
    for item in base[key]:
        x1.append(item[0]/10000)
        y1_base.append(item[1])
        y_base = item[1]
    for item in adv[key]:
        y1_adv.append(item[1])
        y_adv = item[1]
    diff.append(1 - y_adv / y_base)
    axs[i-2].plot(x1, y1_base, marker="o", color="blue", label="Robin Scheduler")
    axs[i-2].plot(x1, y1_adv, marker="x", color="red", label="KeyPath Scheduler")
    axs[i-2].legend()
    axs[i-2].set_title(f"({letters[i-2]}) matrix_num=20,cluster_num={i}")
    axs[i-2].set_xlabel(f"matrix_size(10^4)")
    print(f"diff_avg={np.mean(diff)}")
axs[0].set_ylabel("Latency (s)")
plt.suptitle("Concat's Latency of Different Matrix Size and Cluster Number", fontsize=16)
fig.savefig("concat2.png")
plt.close()


x = []
y1 = []
y2 = []
diff = []
with open("scheduler.json", "r") as f:
    data = json.load(f)
    key = f"matrix_size=100000,cluster_num=4"
    for item in data[key]:
        x.append(item[0])
        y1.append(item[1])
        y2.append(item[2])
        diff.append(item[2] / item[1])

y1 = [math.log(item) for item in y1]
y2 = [math.log(item) for item in y2]
fig, ax1 = plt.subplots(figsize=(16, 6))

ax1.plot(x, y1, marker="o", color="blue", label="Latency")
ax1.plot(x, y2, marker="x", color="red", label="Scheduler Time")
ax1.set_xlabel(f"matrix_num")
ax1.set_ylabel("Time (log)")
ax1.tick_params(axis='y')
ax1.grid(True, alpha=0.3)

ax2 = ax1.twinx()
ax2.set_ylim(0, 0.01)
ax2.bar(x, diff, color="red", alpha=0.5)
ax2.set_ylabel("Scheduler Time Ratio")
ax2.tick_params(axis='y')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
plt.title(f"matrix_size=100000,cluster_num=4")
plt.xlabel(f"matrix_num")
plt.suptitle("Concat's Scheduler Time of Different Matrix Number", fontsize=16)
plt.savefig("concat3.png")
plt.close()

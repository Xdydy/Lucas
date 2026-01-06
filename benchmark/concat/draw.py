import matplotlib.pyplot as plt
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
    axs[i-2].set_title(f"matrix_size=100000,cluster_num={i}")
    axs[i-2].set_xlabel(f"({letters[i-2]}) matrix_num")
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
    axs[i-2].set_title(f"matrix_num=20,cluster_num={i}")
    axs[i-2].set_xlabel(f"({letters[i-2]}) matrix_size(10^4)")
    print(f"diff_avg={np.mean(diff)}")
axs[0].set_ylabel("Latency (s)")
plt.suptitle("Concat's Latency of Different Matrix Size and Cluster Number", fontsize=16)
fig.savefig("concat2.png")
plt.close()

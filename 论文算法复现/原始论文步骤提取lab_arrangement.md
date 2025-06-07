---

---

🧪 一、实验目标回顾
-----------

* 模拟微服务系统故障；

* 利用 Prometheus + Grafana 采集七种指标数据；

* 构建 AutoMAP 异常行为图；

* 执行根因诊断算法；

* 验证与分析诊断精度，复现论文实验结论。

* * *

🏗️ 二、基础平台搭建
------------

### Step 1：部署 Kubernetes 集群

可选方案：

* 本地：Minikube / Kind；

* 云端：Kubernetes on EKS / GKE / AKS；

* 推荐：Minikube + Docker（实验性环境足够）。

```bash
minikube start --cpus=4 --memory=8192
```

* * *

### Step 2：部署微服务系统（Pymicro）

推荐复现论文中使用的 [Pymicro](https://github.com/rshriram/pymicro) 微服务平台：

```bash
git clone https://github.com/rshriram/pymicro
cd pymicro
kubectl apply -f k8s/  # 假设有K8s部署YAML（或将Docker Compose转换）
```

确保部署的服务之间存在典型调用关系，例如 frontend -> API -> database。

包括 16 个 Docker 微服务，由 Zookeeper 管理

* * *

### Step 3：安装 ChaosMesh（故障注入工具）

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-testing --create-namespace --set chaosDaemon.runtime=containerd
```

> 注意：需启用 Webhook 及权限配置，详见 ChaosMesh 官方文档。

* * *

### Step 4：部署 Prometheus + Grafana

使用 kube-prometheus-stack 安装：

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh --namespace=chaos-testing --create-namespace --set chaosDaemon.runtime=containerd
```

确认以下组件运行：

* Prometheus（收集指标）；

* Grafana（展示指标）；

* Node exporter / cAdvisor / kube-state-metrics（收集宿主机资源）。

* * *

### Step 5：配置 Prometheus 采集自定义服务指标

如果服务未自动暴露 `/metrics` 接口：

* 添加 Prometheus exporter（如 `prometheus-client` Python）；

* 或部署 sidecar exporter 容器；

* 配置 `ServiceMonitor` 收集规则。

* * *

🐛 三、故障注入实验设计（ChaosMesh）
------------------------

### Step 6：定义注入场景（模拟论文实验）

#### 场景 A：内存占用异常

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: stress-mem
  namespace: pymicro
spec:
  mode: one
  selector:
    labelSelectors:
      app: service-a
  stressors:
    memory:
      workers: 1
      size: 512Mi
  duration: "60s"

```

#### 场景 B：服务 pod kill

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: kill-service-b
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces: [pymicro]
    labelSelectors:
      app: service-b
  duration: "30s"
```



* * *

📈 四、指标采集与处理
------------

### Step 7：采集 7 类指标

| 指标代码 | 说明     | 来源建议                        |
| ---- | ------ | --------------------------- |
| Mlat | 延迟     | 自定义 `/metrics` 接口、HTTP 请求日志 |
| Mthr | 吞吐     | 请求总数 / 秒                    |
| Mcon | 拥堵度    | Mthr / Mlat                 |
| Mcpu | CPU使用率 | node-exporter               |
| Mio  | IO操作频率 | node-exporter               |
| Mmem | 内存使用率  | node-exporter               |
| Mavl | 可用性    | 200响应率                      |

* 可用 Prometheus 查询语言（PromQL）提取；

* 使用 Python Prometheus HTTP API 导出为 `.csv` 或 `np.array[n_services x t]`。

* * *

🤖 五、执行 AutoMAP 算法流程
--------------------

### Step 8：准备指标数据

```python
metrics_dict = {
  'Mlat': np.array([...]),
  'Mthr': np.array([...]),
  ...
}
```

注意：

* 每个数组形状应为 `[服务数量 × 时间片]`；

* 采样周期建议 5 秒。

* * *

### Step 9：构建异常行为图

```python
G = build_behavior_graph(metrics_dict)
```

使用条件独立性检验（如 χ²）决定服务间是否存在依赖。

* * *

### Step 10：构建服务 profile 和异常 profile

```python
profile = compute_profile(G)
anomaly_profile = current_profile - normal_profile
```

可保存正常运行下的 profile 并在故障发生时对比。

* * *

### Step 11：相似性匹配与诊断指标选择

```python
similar_profiles = find_most_similar_profiles(anomaly_profile, historical_db)
# 自动学习指标权重 w
```

* * *

### Step 12：启发式随机游走定位根因

```python
root_candidates = random_walk_root_cause(G, frontend_id)
top_k = root_candidates[:5]
```

* * *

✅ 六、结果评估与可视化
------------

### Step 13：评估指标计算

对比真实根因服务 ID：

* Top-1 / Top-3 / Top-5 精度；

* avg-5 精度；

* 绘制混淆矩阵、PR 曲线等。

```python
precision = len(set(predicted[:k]) & set(actual_roots)) / len(actual_roots)
```

* * *

### Step 14：可视化输出

* Grafana 仪表盘监控注入前后的指标变化；

* 使用 `networkx` 或 `graphviz` 绘制异常行为图；

* 输出诊断路径、游走轨迹。





一个基础版的 AutoMAP 算法复现代码，包含：

1. **异常行为图构建**（多指标、条件独立性检验）；

2. **服务特征向量（Profile）生成**；

3. **异常相似度匹配**；

4. **启发式随机游走根因定位算法**。

```python
# AutoMAP核心逻辑 - Python伪实现 (需配合Prometheus指标数据使用)
import numpy as np
import networkx as nx
from scipy.stats import chi2_contingency
from sklearn.preprocessing import normalize

# ========== 配置 ==========
ALPHA = 0.01  # 条件独立性显著性水平

# ========== 步骤1: 构建行为图 ==========
def conditional_independence_test(data_i, data_j, data_cond):
    # 使用卡方检验进行条件独立性测试（简化示意）
    contingency_table = np.histogram2d(data_i, data_j)[0]
    chi2, p_value, _, _ = chi2_contingency(contingency_table)
    return p_value > ALPHA

def build_behavior_graph(metrics_dict):
    # metrics_dict: {metric_name: np.array [n_services x time]}
    n_services = next(iter(metrics_dict.values())).shape[0]
    metrics = list(metrics_dict.keys())
    G = nx.DiGraph()

    for i in range(n_services):
        for j in range(n_services):
            if i == j:
                continue
            weights = []
            for metric in metrics:
                data = metrics_dict[metric]
                indep = conditional_independence_test(data[i], data[j], None)  # 简化
                weights.append(0. if indep else 1.)
            if sum(weights) > 0:
                norm_weights = np.array(weights) / np.count_nonzero(weights)
                G.add_edge(i, j, weight=norm_weights)
    return G

# ========== 步骤2: 计算服务 profile ==========
def compute_profile(G):
    profiles = {}
    for node in G.nodes():
        out_edges = G.out_edges(node, data=True)
        if not out_edges:
            profiles[node] = np.zeros(len(next(iter(out_edges), (None, None, {'weight': np.zeros(7)}))[2]['weight']))
            continue
        profile = np.mean([attr['weight'] for _, _, attr in out_edges], axis=0)
        profiles[node] = profile
    return profiles

# ========== 步骤3: Profile 相似度计算 ==========
def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

def find_most_similar_profiles(target_profile, historical_profiles):
    scores = [(idx, cosine_similarity(target_profile, profile)) for idx, profile in historical_profiles.items()]
    return sorted(scores, key=lambda x: -x[1])

# ========== 步骤4: 随机游走根因诊断 ==========
def random_walk_root_cause(G, start_node, steps=1000, rho=0.2):
    visit_count = {node: 0 for node in G.nodes}
    current = start_node
    for _ in range(steps):
        neighbors = list(G.successors(current)) + list(G.predecessors(current)) + [current]
        probs = []
        for n in neighbors:
            if n == current:
                probs.append(0.2)  # self-transition
            elif G.has_edge(current, n):
                probs.append(0.7)
            else:
                probs.append(rho)  # backward
        probs = np.array(probs)
        probs /= probs.sum()
        current = np.random.choice(neighbors, p=probs)
        visit_count[current] += 1
    sorted_nodes = sorted(visit_count.items(), key=lambda x: -x[1])
    return sorted_nodes

# ========== 用法示例 ==========
# 1. metrics_dict = {'Mlat': np.array([...]), 'Mcpu': np.array([...]), ...}
# 2. G = build_behavior_graph(metrics_dict)
# 3. profiles = compute_profile(G)
# 4. similar = find_most_similar_profiles(profiles[frontend_id], historical_profiles)
# 5. ranked_roots = random_walk_root_cause(G, frontend_id)

```

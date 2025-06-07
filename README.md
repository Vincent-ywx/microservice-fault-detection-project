# microservice-fault-detection-project

部署一个微服务系统（SockShop 或更复杂的系统），结合故障注入（ChaosMesh）、监控（Prometheus + Grafana）、测试（Selenium + JMeter）和算法复现（基于论文）来完成一次完整的系统性能评估与故障诊断实验。

## SockShop 微服务部署 (Deployment)

- **进入 SockShop 微服务目录:** 使用命令切换至项目目录，如 `cd D:\microservice-fault-detection-project\demo\microservices-demo`。
- **检查 Kubernetes 集群状态:** 运行 `minikube status` 查看 Minikube 状态。
- **启动 Minikube (Docker 驱动):** 例如 `minikube start --driver=docker`，完成后可部署服务。
- **查看 SockShop 服务列表:** 使用 `kubectl get svc -n sock-shop` 列出所有 SockShop 命名空间下的 Service。
- **检查 Pods:** 运行 `kubectl get pods -n sock-shop` 查看各微服务 Pod 状态。
- **滚动重启部署:** 如需重新部署所有服务，可执行 `kubectl rollout restart deployment -n sock-shop`。重启后效果如下（请插入服务启动效果示意图）。

此处建议插入相关图示: SockShop 服务部署和启动流程示意图。

## SockShop 各 Pod 解释 (Service Structure)

| **Pod 名称 (Name)** | **功能描述 (中文)**                               | **Function Description (English)**                           |
| ------------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| `front-end`         | 用户界面服务，提供 Web 应用界面，调用后端其他服务 | The web UI service; serves the user-facing website and communicates with other services. |
| `carts`             | 购物车服务，处理添加、删除商品等操作              | Manages the shopping cart — add/remove items, retrieve cart contents. |
| `carts-db`          | carts 服务使用的 MongoDB 数据库                   | MongoDB backing the carts service.                           |
| `catalogue`         | 商品目录服务，提供所有商品数据                    | Provides product listings, descriptions, prices, and stock info. |
| `catalogue-db`      | catalogue 使用的 MongoDB 数据库                   | MongoDB for the catalogue service.                           |
| `orders`            | 订单服务，处理下单请求                            | Handles order placement and processing.                      |
| `orders-db`         | orders 服务使用的 MySQL 数据库                    | MySQL used to persist orders.                                |
| `payment`           | 支付服务，模拟支付流程（总是支付成功）            | Simulates a payment process (always succeeds).               |
| `queue-master`      | 用于处理异步任务的服务（如发送邮件）              | Consumes tasks from RabbitMQ queue, e.g., sending confirmation emails. |
| `rabbitmq`          | 消息队列系统，用于服务间异步通信                  | Message broker used for decoupling services (mainly orders + email tasks). |
| `session-db`        | 用户 session 存储服务（Redis）                    | Redis service for storing user sessions (key-value store).   |
| `shipping`          | 发货服务，模拟发货操作                            | Simulates shipping of orders.                                |
| `user`              | 用户账户服务，处理注册、登录等功能                | Manages user registration and authentication.                |
| `user-db`           | user 服务使用的 MySQL 数据库                      | MySQL database backing the user service.                     |

*图示：此处建议插入 SockShop 服务架构图或各服务组件关系图。*

微服务调用关系简图 (Call Graph Overview)

```plaintext
+-------------+
|  front-end  |
+------+------+---------------+------------------+
       |                      |                  |
   [carts]                [user]            [catalogue]
       |                      |                  |
  [carts-db]            [user-db]         [catalogue-db]
       |
   [orders]---[payment]---[shipping]
       |
   [orders-db]
       |
  [queue-master] <--> [rabbitmq]
```

- `front-end` 是唯一直接面向用户的服务，其它服务作为后台支撑。
- 调用关系显示各服务依赖：用户操作通过前端触发，依次调用购物车、用户管理、商品目录、订单等服务。
- **插图**：此处建议插入微服务调用关系示意图或流程图。

# SockShop 架构总结 (Summary)

- **典型电商微服务架构：** 包含用户管理、商品目录、购物车、订单、支付、发货、异步处理等模块，分工明确。

- **服务自治性：** 每个服务职责单一，独立容器部署，提升可维护性和可扩展性。

- **访问示例：** 使用 Minikube 命令启动前端服务并访问：

  ```bash
  minikube service front-end -n sock-shop
  ```

  该命令将在默认浏览器中打开前端界面。

## ChaosMesh 注入 (ChaosMesh Injection)

- **访问实验面板：** ChaosMesh 提供 Web UI 查看故障注入实验结果。执行端口转发：

  ```bash
  kubectl port-forward -n chaos-testing svc/chaos-dashboard 2333:2333
  ```

  然后浏览器访问 `http://localhost:2333` 查看实验情况。

- **获取控制令牌：** 执行以下步骤以生成 ChaosMesh 实验所需的 Token：

  1. 切换到 token 目录：`cd D:\microservice-fault-detection-project\chaosmesh\token`。
  2. 应用权限配置：`kubectl apply -f rbac.yaml`。
  3. 创建 Token：`kubectl create token account-cluster-manager-hrgfu`。
  4. 记录输出的 Token 值（如 `account-cluster-manager-hrgfu`）供后续使用。

此处建议插入 ChaosMesh 实验面板或故障注入流程图。

## Prometheus 监控 (Prometheus Monitoring)

- **查看监控服务：** 列出监控命名空间下的服务：

  ```bash
  kubectl get svc -n monitoring
  ```

  找到 Prometheus 和 Grafana Service 名称。

- **获取访问 URL：** 使用 Minikube 获取 Prometheus/Grafana 的访问地址：

  ```bash
  minikube service prometheus -n monitoring --url
  minikube service grafana -n monitoring --url
  ```

  得到两个 URL，用于访问 Prometheus 和 Grafana UI。

- **限制**：默认监控方案无法直接采集应用的 HTTP 层指标，如延迟或吞吐率。因此需要借助 Istio 注入采集这些应用层指标。

## Istio + Prometheus 集成 (Auto-Instrumentation)

- **AutoMAP 指标需求：** 为支持 AutoMAP 行为图和根因分析，需要采集 HTTP 层指标：

  - **请求延迟 (Mlat, 细粒度延迟指标)**
  - **吞吐率 (Mthr)**
  - **HTTP 状态码可用率 (Mavl)**

- **安装 Istio:** （以 Minikube 为例）

  ```bash
  curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.22.0 sh -
  cd istio-1.22.0
  export PATH=$PWD/bin:$PATH
  istioctl install --set profile=demo -y
  ```

  这将安装 Istio 并部署在 `istio-system` 命名空间。

- **启用 Sidecar 注入：** 给 SockShop 命名空间打标签，启用自动注入：

  ```bash
  kubectl label namespace sock-shop istio-injection=enabled
  ```

  之后重启部署使 Sidecar 注入生效。

- **重新部署 SockShop:** 删除旧的部署清单并重新应用：

  ```bash
  kubectl delete -f complete-demo.yaml -n sock-shop
  kubectl apply -f complete-demo.yaml -n sock-shop
  ```

  所有服务将自动注入 `istio-proxy` Sidecar，用于转发流量和采集指标。

- **访问 Istio Prometheus:** Istio 自带 Prometheus 实例，可直接查询指标：

  ```bash
  kubectl port-forward svc/prometheus -n istio-system 9090:9090
  ```

  然后浏览器打开 `http://localhost:9090` 即可访问。

- **验证注入:** 执行以下命令确认所有 SockShop Pod 都包含 `istio-proxy` 容器：

  ```bash
  kubectl get pods -n sock-shop -o jsonpath="{range .items[*]}{.metadata.name}{'\t'}{range .spec.containers[*]}{.name}{','}{end}{'\n'}{end}" | sort
  ```

  输出的每个 Pod 条目都应包含 `istio-proxy`。

## AutoMAP 行为图指标 (Metrics for AutoMAP)

- **关键性能指标：** 使用以下 PromQL 表达式计算 AutoMAP 所需指标：

  | **指标 (Metric)**   | **PromQL 示例 (Example)**                                    |
  | ------------------- | ------------------------------------------------------------ |
  | **Mlat** (平均延迟) | `rate(istio_request_duration_milliseconds_sum[1m]) / rate(istio_request_duration_milliseconds_count[1m])` |
  | **Mthr** (吞吐率)   | `rate(istio_requests_total[1m])`                             |
  | **Mcon** (并发数)   | `rate(istio_requests_total[1m]) / (rate(istio_request_duration_milliseconds_sum[1m]) / rate(istio_request_duration_milliseconds_count[1m]))` |
  | **Mavl** (可用率)   | `sum(rate(istio_requests_total{response_code=~"2.."}[1m])) / sum(rate(istio_requests_total[1m]))` |

此处建议插入示意图：系统行为图或指标采集流程图。

## AutoMAP 正常负载触发 (Generate Normal Load)

- **基线行为图 (Normal Graph)：** AutoMAP 依赖系统在“稳定运行状态”下的行为图作为基准。首先需确保 SockShop 系统持续一段时间正常运行以生成正常状态的行为图。

- **批量请求生成：** 可使用 Selenium、JMeter 等工具对 `front-end` 服务发起并行压力测试，确保系统产生充足的请求流量。

- **注入故障：** 然后使用 ChaosMesh 对 `front-end` 或其他服务注入延迟或故障。首先检查 ChaosMesh 是否正常：

  ```bash
  kubectl get pods -n chaos-testing
  ```

  确认 `chaos-controller-manager` 等 Pod 已运行。

## AutoMAP 原型框架 (Analysis Framework)

- **数据采集阶段:** 利用上述集成好的 Prometheus 指标持续采集各服务的运行数据。
- **图建模阶段:** 基于调用关系将微服务构建成行为图 (Behavior Graph)，节点属性由指标向量构成。
- **根因定位阶段:** 采用相似度计算和启发式随机游走算法，对当前异常图与正常图进行对比，找出最可能的故障源头。

## AutoMAP 根因定位示例 (Root Cause Analysis)

- **输出示例:** AutoMAP 会返回可疑服务的排序列表。例如：

  ```plaintext
  1. payment (得分: 0.1890)
  2. catalogue (得分: 0.1851)
  3. user (得分: 0.1724)
  … 
  ```

  最高得分（如 `payment`）表示该服务在异常时最可能是根因。

- **用途:** 这样可以加速故障排查，优先关注得分高的服务；并可与注入点比对验证诊断结果，也可用于自动化运维流程（如智能告警或 SLO 分析）。

## AutoMAP 行为图节点 Profile (Node Profiles)

- 每个微服务节点都有一个特征向量（Profile），例如 `front-end profile: [...]`，包含多维指标：
  - **Mlat (延迟)**、**Mcpu (CPU 使用)**、**Mmem (内存使用)**、**Mthr (吞吐率)** 等。
  - 该向量是行为图节点的**语义嵌入**，用于后续的相似度匹配和诊断。
  - 可用于可视化分析，或作为机器学习模型的输入特征。

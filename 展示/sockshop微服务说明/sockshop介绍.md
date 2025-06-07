## 🧩 SockShop 各 Pod 解释（Explanation of SockShop Pods）

| Pod 名称       | 功能描述（中文）                                  | Function Description (English)                               |
| -------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| `front-end`    | 用户界面服务，提供 Web 应用界面，调用后端其他服务 | The web UI service. It serves the user-facing website and communicates with other services. |
| `carts`        | 购物车服务，处理添加、删除商品等操作              | Manages the shopping cart — add/remove items, retrieve cart contents |
| `carts-db`     | carts 服务使用的 MongoDB 数据库                   | MongoDB backing the carts service                            |
| `catalogue`    | 商品目录服务，提供所有商品数据                    | Provides product listings, descriptions, prices, and stock info |
| `catalogue-db` | catalogue 使用的 MongoDB 数据库                   | MongoDB for the catalogue service                            |
| `orders`       | 订单服务，处理下单请求                            | Handles order placement and processing                       |
| `orders-db`    | orders 服务使用的 MySQL 数据库                    | MySQL used to persist orders                                 |
| `payment`      | 支付服务，模拟支付流程（总是支付成功）            | Simulates a payment process (always succeeds)                |
| `queue-master` | 用于处理异步任务的服务（如发送邮件）              | Consumes tasks from RabbitMQ queue, e.g., sending confirmation emails |
| `rabbitmq`     | 消息队列系统，用于服务间异步通信                  | Message broker used for decoupling services (mainly orders + email tasks) |
| `session-db`   | 用户 session 存储服务（Redis）                    | Redis service for storing user sessions (key-value store)    |
| `shipping`     | 发货服务，模拟发货操作                            | Simulates shipping of orders                                 |
| `user`         | 用户账户服务，处理注册、登录等功能                | Manages user registration and authentication                 |
| `user-db`      | user 服务使用的 MySQL 数据库                      | MySQL database backing the user service                      |



------

## 🧠 微服务调用关系简图（Call Graph Overview）

```
sql复制编辑+-------------+
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

> `front-end` 是唯一直接面向用户的服务，其它服务都是后台支撑。

------

## 📌总结：

SockShop 是一个典型的电商微服务架构示例，模块划分清晰：

- 包括用户管理、商品、购物车、订单、支付、发货、异步处理等核心电商模块。
- 每个服务职责单一，使用独立容器部署，具备良好的“微服务自治性”。
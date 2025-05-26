#!/bin/bash

# 一键部署 Hotel Reservation 微服务到 Minikube 的脚本
# Author: 你的小组名
# Date: 2025-05-XX

set -e  # 遇到错误立即退出

# 定义颜色用于输出美观
GREEN='\033[0;32m'
NC='\033[0m' # 无色

echo -e "${GREEN}🏗️ Step 1: 启动 Minikube...${NC}"
minikube start --driver=docker

echo -e "${GREEN}🔄 Step 2: 切换到 minikube-docker 环境（将镜像构建到集群内）...${NC}"
eval $(minikube docker-env)

echo -e "${GREEN}🐳 Step 3: 构建所有微服务 Docker 镜像...${NC}"
SERVICES=("geo" "profile" "rate" "recommendation" "reservation" "search" "user")
for service in "${SERVICES[@]}"; do
  echo -e "${GREEN}🔧 构建服务：$service${NC}"
  docker build -t hotel_$service ./docker/hotel-reservation/$service
done

echo -e "${GREEN}📦 Step 4: 创建 Kubernetes namespace：hotel-reservation${NC}"
kubectl create namespace hotel-reservation || echo "(已存在)"

echo -e "${GREEN}🚀 Step 5: 部署微服务到 K8s 集群中...${NC}"
kubectl apply -n hotel-reservation -f ./k8s-manifests/hotel-reservation/

echo -e "${GREEN}🌐 Step 6: 配置 Ingress 或 NodePort 访问入口（可选）${NC}"
# 示例：开启一个 NodePort 暴露 search 服务
kubectl expose deployment search --type=NodePort --name=search-service -n hotel-reservation

echo -e "${GREEN}⏳ Step 7: 等待所有 Pod 启动...${NC}"
kubectl wait --for=condition=Ready pods --all -n hotel-reservation --timeout=180s

echo -e "${GREEN}✅ Hotel Reservation 微服务已成功部署！${NC}"
echo -e "${GREEN}🌐 访问地址:${NC}"
minikube service search-service -n hotel-reservation


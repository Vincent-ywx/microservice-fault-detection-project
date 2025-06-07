import numpy as np
import networkx as nx
import datetime
from prometheus_api_client import PrometheusConnect
from scipy.stats import chi2_contingency
from sklearn.metrics.pairwise import cosine_similarity
import warnings

warnings.filterwarnings("ignore")

PROMETHEUS_URL = "http://localhost:9090"
prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)

SERVICES = [
    "front-end", "carts", "orders", "user", "payment", "shipping", "catalogue"
]

METRICS = ["Mlat", "Mthr", "Mcon", "Mcpu", "Mio", "Mmem", "Mavl"]

METRIC_QUERIES = {
    "Mlat": 'rate(istio_request_duration_milliseconds_sum{{destination_service_name="{svc}"}}[1m]) / rate(istio_request_duration_milliseconds_count{{destination_service_name="{svc}"}}[1m])',
    "Mthr": 'rate(istio_requests_total{{destination_service_name="{svc}"}}[1m])',
    "Mcon": 'rate(istio_requests_total{{destination_service_name="{svc}"}}[1m]) / (rate(istio_request_duration_milliseconds_sum{{destination_service_name="{svc}"}}[1m]) / rate(istio_request_duration_milliseconds_count{{destination_service_name="{svc}"}}[1m]))',
    "Mavl": 'sum(rate(istio_requests_total{{destination_service_name="{svc}", response_code=~"2.."}}[1m])) / sum(rate(istio_requests_total{{destination_service_name="{svc}"}}[1m]))',
    "Mcpu": 'rate(container_cpu_usage_seconds_total{{pod=~"{svc}.*"}}[1m])',
    "Mio": 'rate(container_fs_reads_bytes_total{{pod=~"{svc}.*"}}[1m]) + rate(container_fs_writes_bytes_total{{pod=~"{svc}.*"}}[1m])',
    "Mmem": 'container_memory_usage_bytes{{pod=~"{svc}.*"}}'
}

END_TIME = datetime.datetime.utcnow()
START_TIME = END_TIME - datetime.timedelta(minutes=5)
STEP = "15s"

def conditional_independence_test(x, y):
    contingency_table = np.histogram2d(x, y, bins=10)[0]
    if np.any(contingency_table == 0):
        return False
    chi2, p_value, _, _ = chi2_contingency(contingency_table)
    return p_value > 0.05

def fetch_metrics(prom, metric_type, services):
    data = {}
    fixed_length = 20
    for svc in services:
        print(f"获取指标: {metric_type} @ {svc}")
        query = METRIC_QUERIES[metric_type].format(svc=svc)
        try:
            result = prom.custom_query_range(
                query=query,
                start_time=START_TIME,
                end_time=END_TIME,
                step=STEP
            )
            svc_data = []
            for ts in result:
                values = [float(val[1]) for val in ts["values"] if val[1] != "NaN"]
                svc_data.extend(values)
            if len(svc_data) < fixed_length:
                svc_data.extend([0] * (fixed_length - len(svc_data)))
            else:
                svc_data = svc_data[:fixed_length]
            data[svc] = np.array(svc_data)
        except Exception as e:
            print(f"[错误] Prometheus 查询失败: {e}")
            data[svc] = np.zeros(fixed_length)
    return data

def get_all_metrics(prom):
    metrics_dict = {}
    for metric in METRICS:
        metrics_dict[metric] = fetch_metrics(prom, metric, SERVICES)
    return metrics_dict

def build_behavior_graph(metrics_dict):
    G = nx.Graph()
    for idx, svc in enumerate(SERVICES):
        G.add_node(idx, name=svc)
    for i in range(len(SERVICES)):
        for j in range(i + 1, len(SERVICES)):
            connected = False
            for metric in METRICS:
                data = metrics_dict[metric]
                indep = conditional_independence_test(data[SERVICES[i]], data[SERVICES[j]])
                if not indep:
                    connected = True
                    break
            if connected:
                G.add_edge(i, j)
    return G

def compute_profiles(metrics_dict):
    profiles = {}
    fixed_length = 20
    for idx, svc in enumerate(SERVICES):
        profile = []
        for metric in METRICS:
            vec = metrics_dict[metric].get(svc, np.zeros(fixed_length))
            if len(vec) < fixed_length:
                vec = np.pad(vec, (0, fixed_length - len(vec)), 'constant')
            elif len(vec) > fixed_length:
                vec = vec[:fixed_length]
            profile.extend(vec)
        profiles[idx] = np.array(profile)
    return profiles

def compute_similarity_matrix(profiles):
    mat = np.array(list(profiles.values()))
    sim = cosine_similarity(mat)
    return sim

def random_walk_ranking(G, scores, restart_prob=0.7, max_iter=100):
    nodes = list(G.nodes)
    A = nx.adjacency_matrix(G).astype(float)
    A = A.todense()
    n = len(nodes)
    A = A / A.sum(axis=1, keepdims=True)
    p = np.ones((n, 1)) / n
    r = scores.reshape((n, 1))

    for _ in range(max_iter):
        p = (1 - restart_prob) * A @ p + restart_prob * r

    ranking = {nodes[i]: p[i, 0] for i in range(n)}
    return sorted(ranking.items(), key=lambda x: x[1], reverse=True)

if __name__ == "__main__":
    metrics_dict = get_all_metrics(prom)
    G = build_behavior_graph(metrics_dict)
    print(f"\n 行为图节点数: {G.number_of_nodes()}")
    print(f" 行为图边数: {G.number_of_edges()}")

    profiles = compute_profiles(metrics_dict)
    frontend_id = SERVICES.index("front-end")
    print(f"\n front-end profile 长度: {len(profiles[frontend_id])}")

    sim_matrix = compute_similarity_matrix(profiles)
    anomaly_score = np.array([np.linalg.norm(profiles[i] - profiles[frontend_id]) for i in range(len(SERVICES))])
    anomaly_score = anomaly_score / np.sum(anomaly_score)

    ranking = random_walk_ranking(G, anomaly_score)
    print("\n 根因服务排名：")
    for rank, (svc_idx, score) in enumerate(ranking):
        print(f"{rank + 1}. {SERVICES[svc_idx]}（得分: {score:.4f}）")

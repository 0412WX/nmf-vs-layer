import json
import sys
import math
from collections import defaultdict

class SubGraph:
    def __init__(self):
        self.layer_start = 0
        self.layer_end = 0
        self.path_segments = set()
        self.nodes = set()
        self.edges = set()

def build_dag(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    parser = data['parsers'][0]
    start_state = parser['start_state']
    nodes = parser['nodes']
    edges = parser['edges']
    
    adj = defaultdict(list)
    for edge in edges:
        src = edge['src']
        dst = edge['dst']
        adj[src].append(dst)
    
    # 识别出度为零的节点作为终止节点
    terminals = set()
    for node in nodes:
        if node not in adj or len(adj[node]) == 0:
            terminals.add(node)
    
    # 如果没有出度为零的节点，默认使用{'accept'}作为终止节点
    if not terminals:
        terminals = {'accept'}
    
    return {
        'start_state': start_state,
        'nodes': nodes,
        'adj': adj,
        'terminals': terminals
    }

def extract_paths(dag):
    paths = []
    start_state = dag['start_state']
    adj = dag['adj']
    terminals = dag['terminals']
    
    def dfs(node, current_path):
        current_path.append(node)
        if node in terminals:
            paths.append(current_path.copy())
            current_path.pop()
            return
        for next_node in adj.get(node, []):
            if next_node not in current_path:
                dfs(next_node, current_path)
        current_path.pop()
    
    dfs(start_state, [])
    return paths

def extract_unique_node_paths(dag):
    """提取唯一的节点集合路径"""
    all_paths = extract_paths(dag)
    unique_paths = set()
    for path in all_paths:
        # 将路径转换为节点集合的frozenset，以去重
        node_set = frozenset(path)
        unique_paths.add(node_set)
    return list(unique_paths)

def compute_layer_diversity(paths):
    if not paths:
        return [], 0
    
    max_depth = max(len(p) - 1 for p in paths)
    diversity = [0] * (max_depth + 1)
    
    for d in range(max_depth + 1):
        nodes_at_d = set()
        for path in paths:
            if d < len(path):
                nodes_at_d.add(path[d])
        diversity[d] = len(nodes_at_d)
    
    return diversity, max_depth

def layer_cut(diversity, max_depth, W, MIN_D):
    cut_points = [0]
    last_cut = 0
    prev_direction = None
    
    for d in range(1, max_depth + 1):
        diff = diversity[d] - diversity[d - 1]
        if diff > 0:
            curr_direction = 'UP'
        elif diff < 0:
            curr_direction = 'DOWN'
        else:
            curr_direction = 'FLAT'
        
        if curr_direction != 'FLAT':
            if prev_direction is not None and curr_direction != prev_direction:
                if d - last_cut >= MIN_D:
                    cut_points.append(d)
                    last_cut = d
                    prev_direction = None
                    continue
            prev_direction = curr_direction
        
        if d - last_cut >= W:
            cut_points.append(d)
            last_cut = d
            prev_direction = None
    
    if cut_points[-1] != max_depth:
        cut_points.append(max_depth)
    
    return cut_points

def count_path_segments(paths, layer_start, layer_end):
    segments = set()
    for path in paths:
        if len(path) - 1 < layer_start:
            continue
        seg_end = min(layer_end, len(path) - 1)
        segment = tuple(path[layer_start:seg_end + 1])
        segments.add(segment)
    return len(segments)

def dp_merge(paths, cut_points, W, k_min=2, k_max=10):
    m = len(cut_points) - 1
    
    INF = float('inf')
    pc = [[INF] * (m + 1) for _ in range(m + 1)]
    
    for i in range(m):
        for j in range(i + 1, m + 1):
            merged_depth = cut_points[j] - cut_points[i]
            if merged_depth > W:
                break
            pc[i][j] = count_path_segments(paths, cut_points[i], cut_points[j])
    
    g_max = min(k_max, m)
    g_min = max(k_min, 1)
    
    dp = [[INF] * (g_max + 1) for _ in range(m + 1)]
    dp[0][0] = 0
    
    choice = [[-1] * (g_max + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for g in range(1, min(i, g_max) + 1):
            for j in range(g - 1, i):
                merged_depth = cut_points[i] - cut_points[j]
                if merged_depth > W:
                    continue
                if dp[j][g - 1] == INF:
                    continue
                cost = dp[j][g - 1] + pc[j][i]
                if cost < dp[i][g]:
                    dp[i][g] = cost
                    choice[i][g] = j
    
    best_g = -1
    best_cost = INF
    for g in range(g_min, g_max + 1):
        if dp[m][g] < best_cost:
            best_cost = dp[m][g]
            best_g = g
    
    if best_g == -1:
        print(f"警告: 无法满足子图数约束[{k_min},{k_max}]且W={W}的硬约束，返回初始切分结果")
        total_cost = sum(pc[i-1][i] for i in range(1, m+1))
        return cut_points, total_cost, m
    
    merge_points = [cut_points[m]]
    idx = m
    g = best_g
    while g > 0:
        j = choice[idx][g]
        merge_points.insert(0, cut_points[j])
        idx = j
        g -= 1
    
    return merge_points, best_cost, best_g

def build_final_subgraphs(paths, merge_points):
    k = len(merge_points) - 1
    subgraphs = []
    
    for i in range(k):
        sg = SubGraph()
        sg.layer_start = merge_points[i]
        sg.layer_end = merge_points[i + 1]
        
        for path in paths:
            if len(path) - 1 < sg.layer_start:
                continue
            seg_end = min(sg.layer_end, len(path) - 1)
            segment = path[sg.layer_start:seg_end + 1]
            sg.path_segments.add(tuple(segment))
            
            for idx in range(len(segment)):
                sg.nodes.add(segment[idx])
                if idx + 1 < len(segment):
                    sg.edges.add((segment[idx], segment[idx + 1]))
        
        subgraphs.append(sg)
    
    return subgraphs

def verify_partition(subgraphs, original_paths, merge_points):
    for path in original_paths:
        for i in range(len(subgraphs)):
            sg = subgraphs[i]
            if len(path) - 1 < sg.layer_start:
                break
            seg_end = min(sg.layer_end, len(path) - 1)
            segment = tuple(path[sg.layer_start:seg_end + 1])
            assert segment in sg.path_segments, f"路径段丢失: {segment}"
    
    for i in range(len(subgraphs) - 1):
        end_nodes = {seg[-1] for seg in subgraphs[i].path_segments}
        start_nodes = {seg[0] for seg in subgraphs[i+1].path_segments}
        assert start_nodes.issubset(end_nodes), f"子图边界断裂: 子图{i}末层缺少节点{start_nodes - end_nodes}"
    
    for i, sg in enumerate(subgraphs):
        assert len(sg.path_segments) > 0, f"空子图: {i}"
    
    total_segments = sum(len(sg.path_segments) for sg in subgraphs)
    print(f"路径段总数: {total_segments}")
    print(f"原始路径数: {len(original_paths)}")

def check_balance(subgraphs, threshold=3.0):
    sizes = [len(sg.path_segments) for sg in subgraphs]
    if not sizes:
        return 0
    avg = sum(sizes) / len(sizes)
    if avg == 0:
        return 0
    max_ratio = max(sizes) / avg
    
    if max_ratio > threshold:
        print(f"警告: 子图不均衡: 最大子图路径段数为平均值的{round(max_ratio, 1)}倍")
        print(f"  各子图路径段数: {sizes}")
        print("  建议: 调小W或增大k_max以获得更均衡的划分")
    
    return max_ratio

def main(json_file, W=None, MIN_D=2, k_min=2, k_max=10):
    print("═══════════════ 开始执行 DAG 子图划分算法 ═══════════════")
    
    dag = build_dag(json_file)
    paths = extract_paths(dag)
    unique_node_paths = extract_unique_node_paths(dag)
    
    if not paths:
        print("错误: 无有效路径")
        return
    
    diversity, max_depth = compute_layer_diversity(paths)
    
    if W is None:
        W = max(3, math.ceil(max_depth / 2))
    
    print(f"DAG最大深度: {max_depth}")
    print(f"固定窗口宽度W: {W}")
    print(f"原始路径数: {len(paths)}")
    print(f"唯一节点路径数: {len(unique_node_paths)}")
    print(f"层级多样性: {diversity}")
    
    cut_points = layer_cut(diversity, max_depth, W, MIN_D)
    initial_subgraph_count = len(cut_points) - 1
    print(f"初始切分点: {cut_points}")
    print(f"初始子图数: {initial_subgraph_count}")
    
    if initial_subgraph_count < k_min:
        W_retry = max(2, W // 2)
        cut_points = layer_cut(diversity, max_depth, W_retry, MIN_D)
        initial_subgraph_count = len(cut_points) - 1
        if initial_subgraph_count < k_min:
            print(f"警告: DAG深度不足以划分为{k_min}个子图")
            step = max(1, max_depth // k_min)
            cut_points = [i * step for i in range(k_min)] + [max_depth]
            cut_points = sorted(list(set(cut_points)))
            print(f"强制切分点: {cut_points}")
    
    merge_points, best_cost, best_g = dp_merge(paths, cut_points, W, k_min, k_max)
    print(f"合并后切分点: {merge_points}")
    print(f"最终子图数: {best_g}")
    print(f"最小路径段总数: {best_cost}")
    
    subgraphs = build_final_subgraphs(paths, merge_points)
    verify_partition(subgraphs, paths, merge_points)
    check_balance(subgraphs)
    
    print("\n═══════════════ 划分结果 ═══════════════")
    print(f"最终子图数: {best_g}")
    print(f"原图完整路径数: {len(paths)}")
    print(f"唯一节点路径数: {len(unique_node_paths)}")
    print(f"所有子图路径段总数: {best_cost}")
    
    result = {
        "subgraphs": [],
        "total_segments": best_cost,
        "original_paths_count": len(paths),
        "unique_node_paths_count": len(unique_node_paths)
    }
    
    for i, sg in enumerate(subgraphs):
        print(f"子图 {i+1}: 层级[{sg.layer_start}, {sg.layer_end}], "
              f"{len(sg.path_segments)} 条路径段, "
              f"{len(sg.nodes)} 个节点, {len(sg.edges)} 条边")
        
        sg_info = {
            "id": i+1,
            "layer_start": sg.layer_start,
            "layer_end": sg.layer_end,
            "path_segments_count": len(sg.path_segments),
            "nodes_count": len(sg.nodes),
            "edges_count": len(sg.edges),
            "path_segments": [" → ".join(seg) for seg in sg.path_segments]
        }
        result["subgraphs"].append(sg_info)
        
        for seg in sg.path_segments:
            print(f"  {' → '.join(seg)}")
    
    output_file = json_file.replace('.json', '_partition_result.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    return subgraphs, best_cost

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='基于层级多样性拐点切分与动态规划合并的 DAG 子图划分算法')
    parser.add_argument('json_file', help='P4 解析图 JSON 文件路径')
    parser.add_argument('--W', type=int, help='固定窗口宽度')
    parser.add_argument('--MIN_D', type=int, default=2, help='最小切分间距')
    parser.add_argument('--k_min', type=int, default=2, help='最小子图数')
    parser.add_argument('--k_max', type=int, default=10, help='最大子图数')
    
    args = parser.parse_args()
    main(args.json_file, args.W, args.MIN_D, args.k_min, args.k_max)

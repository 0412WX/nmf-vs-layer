import os
import json
from collections import defaultdict

def is_dag(graph, start_node):
    visited = set()
    rec_stack = set()
    
    def has_cycle(node):
        if node in rec_stack:
            return True
        if node in visited:
            return False
        
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in graph.get(node, []):
            if has_cycle(neighbor):
                return True
        
        rec_stack.remove(node)
        return False
    
    return not has_cycle(start_node)

def remove_cycles(graph, start_node):
    visited = set()
    rec_stack = set()
    cycles = []
    
    def find_cycles(node, path):
        if node in rec_stack:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:])
            return
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in graph.get(node, []):
            find_cycles(neighbor, path + [node])
        
        rec_stack.remove(node)
    
    find_cycles(start_node, [])
    
    for cycle in cycles:
        for i in range(len(cycle)):
            src = cycle[i]
            dst = cycle[(i + 1) % len(cycle)]
            if dst in graph.get(src, []):
                graph[src].remove(dst)
    
    return graph

def count_unique_paths(graph, start_node, end_node):
    memo = {}
    
    def dfs(node):
        if node == end_node:
            return 1
        if node in memo:
            return memo[node]
        
        count = 0
        for neighbor in graph.get(node, []):
            count += dfs(neighbor)
        
        memo[node] = count
        return count
    
    return dfs(start_node)

def process_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = []
    
    for parser in data.get('parsers', []):
        parser_name = parser.get('parser_name')
        start_state = parser.get('start_state')
        edges = parser.get('edges', [])
        nodes = parser.get('nodes', [])
        
        graph = defaultdict(list)
        for edge in edges:
            src = edge.get('src')
            dst = edge.get('dst')
            if src and dst:
                graph[src].append(dst)
        
        is_directed_acyclic = is_dag(graph, start_state)
        
        if not is_directed_acyclic:
            graph = remove_cycles(graph, start_state)
        
        end_nodes = ['accept', 'reject']
        end_node = None
        for node in end_nodes:
            if node in nodes:
                end_node = node
                break
        
        if not end_node:
            sinks = []
            for node in nodes:
                if node not in graph or len(graph[node]) == 0:
                    sinks.append(node)
            if sinks:
                end_node = sinks[0]
            else:
                end_node = nodes[-1]
        
        unique_paths = count_unique_paths(graph, start_state, end_node)
        
        results.append({
            'parser_name': parser_name,
            'is_dag': is_directed_acyclic,
            'unique_paths': unique_paths,
            'start_node': start_state,
            'end_node': end_node
        })
    
    return results

def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    
    all_results = []
    
    for json_file in json_files:
        file_path = os.path.join(directory, json_file)
        print(f"Processing {json_file}...")
        
        try:
            results = process_json_file(file_path)
            all_results.append({
                'file': json_file,
                'parsers': results
            })
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    print("\n===== Summary =====")
    for result in all_results:
        print(f"\nFile: {result['file']}")
        for parser in result['parsers']:
            print(f"  Parser: {parser['parser_name']}")
            print(f"  Is DAG: {parser['is_dag']}")
            print(f"  Unique paths: {parser['unique_paths']}")
            print(f"  Start node: {parser['start_node']}")
            print(f"  End node: {parser['end_node']}")

if __name__ == "__main__":
    main()
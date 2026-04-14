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

def process_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for parser in data.get('parsers', []):
        start_state = parser.get('start_state')
        edges = parser.get('edges', [])
        
        graph = defaultdict(list)
        for edge in edges:
            src = edge.get('src')
            dst = edge.get('dst')
            if src and dst:
                graph[src].append(dst)
        
        is_directed_acyclic = is_dag(graph, start_state)
        
        if not is_directed_acyclic:
            graph = remove_cycles(graph, start_state)
            
            new_edges = []
            edge_map = set()
            for edge in edges:
                src = edge.get('src')
                dst = edge.get('dst')
                if src and dst and dst in graph.get(src, []):
                    edge_key = f"{src}->{dst}"
                    if edge_key not in edge_map:
                        new_edges.append(edge)
                        edge_map.add(edge_key)
            
            parser['edges'] = new_edges
            parser['num_edges'] = len(new_edges)
            
            sparse_matrix = parser.get('sparse_matrix', {})
            if sparse_matrix:
                entries = sparse_matrix.get('entries', [])
                new_entries = []
                for entry in entries:
                    src = entry.get('src')
                    dst = entry.get('dst')
                    if src and dst and dst in graph.get(src, []):
                        new_entries.append(entry)
                
                sparse_matrix['entries'] = new_entries
                sparse_matrix['data'] = [1] * len(new_entries)
                sparse_matrix['rows'] = [entry.get('row') for entry in new_entries]
                sparse_matrix['cols'] = [entry.get('col') for entry in new_entries]
    
    return data

def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    
    for json_file in json_files:
        file_path = os.path.join(directory, json_file)
        print(f"Processing {json_file}...")
        
        try:
            modified_data = process_json_file(file_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(modified_data, f, indent=2)
            
            print(f"Successfully converted {json_file} to DAG")
        except Exception as e:
            print(f"Error processing {json_file}: {e}")

if __name__ == "__main__":
    main()
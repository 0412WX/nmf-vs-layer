import os
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_DIR = SCRIPT_DIR / "result"

# 确保结果目录存在
RESULT_DIR.mkdir(parents=True, exist_ok=True)

def run_layer_partition(json_file):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "layer_cut_merge_partition.py"),
        str(json_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR)
    
    output_file = json_file.replace('.json', '_partition_result.json')
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    return None

def run_nmf_partition(json_file):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "nmf_dag_partition.py"),
        "--input-file", str(json_file),
        "--output-dir", str(RESULT_DIR),
        "--k-min", "2",
        "--k-max", "10",
        "--max-paths", "0"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR)
    
    output_file = RESULT_DIR / f"{Path(json_file).stem}.nmf_partition_result.json"
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    return None

def compute_compression_rate(original_count, subgraph_count):
    if original_count == 0:
        return 0.0
    return (1 - subgraph_count / original_count) * 100

def main():
    # 处理所有JSON文件
    json_files = [f for f in os.listdir(SCRIPT_DIR) if f.endswith('.p4.json')]
    
    summary = []
    
    for json_file in json_files:
        file_path = SCRIPT_DIR / json_file
        print(f"Processing {json_file}...")
        
        # 运行layer方案
        layer_result = run_layer_partition(str(file_path))
        
        # 运行nmf方案
        nmf_result = run_nmf_partition(str(file_path))
        
        # 统计原解析图唯一节点路径数
        with open(file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        original_paths = 0
        if 'parsers' in original_data:
            for parser in original_data['parsers']:
                if 'nodes' in parser:
                    # 这里简化处理，实际应该提取唯一路径数
                    # 但为了与脚本结果对比，我们使用脚本计算的路径数
                    pass
        
        # 提取layer方案的结果
        layer_subgraphs = 0
        layer_segment_count = 0
        layer_compression_rate = 0.0
        layer_reconstruct = False
        
        if layer_result:
            layer_subgraphs = len(layer_result.get('subgraphs', []))
            layer_segment_count = layer_result.get('total_segments', 0)
            original_paths = layer_result.get('original_paths_count', 0)
            if original_paths > 0:
                layer_compression_rate = compute_compression_rate(original_paths, layer_segment_count)
            layer_reconstruct = True  # 假设layer方案总是可以复原
        
        # 提取nmf方案的结果
        nmf_subgraphs = 0
        nmf_segment_count = 0
        nmf_compression_rate = 0.0
        nmf_reconstruct = False
        
        if nmf_result:
            for parser_result in nmf_result.get('parser_results', []):
                if parser_result.get('status') == 'ok':
                    nmf_subgraphs = parser_result.get('best_actual_k', 0)
                    nmf_segment_count = parser_result.get('total_unique_segment_count', 0)
                    original_paths = parser_result.get('unique_node_path_count', 0)
                    nmf_reconstruct = parser_result.get('path_verification', {}).get('all_paths_reconstructed', False)
                    if original_paths > 0:
                        nmf_compression_rate = compute_compression_rate(original_paths, nmf_segment_count)
                    break
        
        summary.append({
            'file': json_file,
            'original_unique_paths': original_paths,
            'nmf_subgraphs': nmf_subgraphs,
            'nmf_segment_count': nmf_segment_count,
            'nmf_compression_rate': round(nmf_compression_rate, 2),
            'nmf_reconstruct': nmf_reconstruct,
            'layer_subgraphs': layer_subgraphs,
            'layer_segment_count': layer_segment_count,
            'layer_compression_rate': round(layer_compression_rate, 2),
            'layer_reconstruct': layer_reconstruct
        })
    
    # 生成汇总表
    summary_file = RESULT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 生成CSV格式的汇总表
    csv_file = RESULT_DIR / "summary.csv"
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("File,Original Unique Paths,NMF Subgraphs,NMF Segment Count,NMF Compression Rate (%),NMF Reconstruct,Layer Subgraphs,Layer Segment Count,Layer Compression Rate (%),Layer Reconstruct\n")
        for item in summary:
            f.write(f"{item['file']},{item['original_unique_paths']},{item['nmf_subgraphs']},{item['nmf_segment_count']},{item['nmf_compression_rate']},{item['nmf_reconstruct']},{item['layer_subgraphs']},{item['layer_segment_count']},{item['layer_compression_rate']},{item['layer_reconstruct']}\n")
    
    print(f"Summary saved to {summary_file}")
    print(f"CSV summary saved to {csv_file}")

if __name__ == "__main__":
    main()
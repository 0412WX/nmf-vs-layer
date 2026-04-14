from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
LOCAL_DEPS_DIR = SCRIPT_DIR / "_pydeps"
if LOCAL_DEPS_DIR.exists():
    sys.path.insert(0, str(LOCAL_DEPS_DIR))

# Add E drive dependencies
e_deps_dir = Path("E:\SpMM_Parser-master\graph\_pydeps")
if e_deps_dir.exists():
    sys.path.insert(0, str(e_deps_dir))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import norm as sparse_norm
from sklearn.decomposition import NMF
from sklearn.exceptions import ConvergenceWarning


Transition = Tuple[str, str, str]


@dataclass(frozen=True)
class PathRecord:
    nodes: Tuple[str, ...]
    transitions: Tuple[Transition, ...]


@dataclass
class ParserDAG:
    parser_name: str
    nodes: List[str]
    adj: Dict[str, List[Tuple[str, str]]]
    start_state: str
    terminals: set[str]
    edges: set[Transition]


NodePathKey = Tuple[str, ...]
SegmentKey = Tuple[str, ...]
HARD_MAX_SEGMENT_NODES = 6


def _transition_to_dict(transition: Transition) -> Dict:
    src, dst, cond = transition
    return {"src": src, "dst": dst, "condition": cond}


def _transitions_to_dicts(transitions: Sequence[Transition]) -> List[Dict]:
    return [_transition_to_dict(t) for t in transitions]


def _transition_dict_to_tuple(transition: Dict) -> Transition:
    return (
        str(transition.get("src", "")),
        str(transition.get("dst", "")),
        str(transition.get("condition", "")),
    )


def build_dags_from_json(payload: Dict) -> List[ParserDAG]:
    dags: List[ParserDAG] = []
    for parser_obj in payload.get("parsers", []):
        parser_name = str(parser_obj.get("parser_name", "unknown_parser"))
        start_state = str(parser_obj.get("start_state", ""))
        nodes = [str(n) for n in parser_obj.get("nodes", [])]
        edge_objs = parser_obj.get("edges", [])

        adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        node_set = set(nodes)
        edge_set: set[Transition] = set()
        for e in edge_objs:
            src = str(e.get("src", ""))
            dst = str(e.get("dst", ""))
            cond = str(e.get("condition", ""))
            if not src or not dst:
                continue
            adj[src].append((dst, cond))
            node_set.add(src)
            node_set.add(dst)
            edge_set.add((src, dst, cond))

        if start_state:
            node_set.add(start_state)

        terminals: set[str] = set()
        for n in node_set:
            if n.lower() in {"accept", "reject"} or len(adj.get(n, [])) == 0:
                terminals.add(n)

        dags.append(
            ParserDAG(
                parser_name=parser_name,
                nodes=sorted(node_set),
                adj=dict(adj),
                start_state=start_state,
                terminals=terminals,
                edges=edge_set,
            )
        )
    return dags


def enumerate_paths(
    dag: ParserDAG,
    max_paths: int | None = None,
) -> Tuple[List[PathRecord], bool]:
    if not dag.start_state:
        return [], False

    paths: List[PathRecord] = []
    truncated = False

    current_nodes: List[str] = []
    current_transitions: List[Transition] = []
    on_path: set[str] = set()

    def dfs(node: str) -> None:
        nonlocal truncated
        if truncated:
            return

        current_nodes.append(node)
        on_path.add(node)

        if node in dag.terminals:
            paths.append(
                PathRecord(
                    nodes=tuple(current_nodes),
                    transitions=tuple(current_transitions),
                )
            )
            if max_paths is not None and len(paths) >= max_paths:
                truncated = True
        else:
            for dst, cond in dag.adj.get(node, []):
                if truncated:
                    break
                if dst in on_path:
                    continue
                current_transitions.append((node, dst, cond))
                dfs(dst)
                current_transitions.pop()

        on_path.remove(node)
        current_nodes.pop()

    dfs(dag.start_state)
    return paths, truncated


def deduplicate_paths_by_nodes(paths: Sequence[PathRecord]) -> Tuple[List[PathRecord], int]:
    unique_paths: Dict[NodePathKey, PathRecord] = {}
    duplicate_count = 0
    for path in paths:
        if path.nodes in unique_paths:
            duplicate_count += 1
            continue
        unique_paths[path.nodes] = path
    return list(unique_paths.values()), duplicate_count


def build_virtual_node_matrix(
    paths: Sequence[PathRecord],
) -> Tuple[sp.csr_matrix, Dict[Tuple[str, int], int]]:
    vnode_index: Dict[Tuple[str, int], int] = {}

    rows: List[int] = []
    cols: List[int] = []
    data: List[float] = []
    for row, path in enumerate(paths):
        for depth, node in enumerate(path.nodes):
            key = (node, depth)
            if key not in vnode_index:
                vnode_index[key] = len(vnode_index)
            rows.append(row)
            cols.append(vnode_index[key])
            data.append(1.0)

    matrix = sp.csr_matrix(
        (np.asarray(data, dtype=np.float32), (rows, cols)),
        shape=(len(paths), len(vnode_index)),
        dtype=np.float32,
    )
    return matrix, vnode_index


def nmf_decompose(
    V: sp.csr_matrix,
    k: int,
    n_restarts: int,
    max_iter: int,
    tol: float,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray, float]:
    if k <= 0:
        raise ValueError("k must be positive")
    if k > min(V.shape):
        raise ValueError(f"k={k} is larger than min(V.shape)={min(V.shape)}")

    best_W: np.ndarray | None = None
    best_H: np.ndarray | None = None
    best_error = math.inf

    denom = float(sparse_norm(V))
    if denom <= 0:
        denom = 1.0

    for trial in range(max(1, n_restarts)):
        init = "nndsvda" if trial == 0 else "random"
        random_state = None if trial == 0 else seed + trial
        model = NMF(
            n_components=k,
            init=init,
            solver="cd",
            max_iter=max_iter,
            tol=tol,
            random_state=random_state,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            W = model.fit_transform(V)
        H = model.components_
        error = float(model.reconstruction_err_) / denom
        if error < best_error:
            best_error = error
            best_W = W
            best_H = H

    if best_W is None or best_H is None:
        raise RuntimeError("NMF decomposition failed for all restarts")
    return best_W, best_H, best_error


def min_max_normalize(values: Sequence[float]) -> List[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _segment_key(nodes: Sequence[str]) -> SegmentKey:
    return tuple(nodes)


def _segment_to_dict(
    seg_id: str,
    key: SegmentKey,
    usage_count: int,
    transitions: Sequence[Transition],
) -> Dict:
    nodes = key
    return {
        "segment_id": seg_id,
        "usage_count": int(usage_count),
        "depth_nodes": len(nodes),
        "depth_edges": max(0, len(nodes) - 1),
        "start_node": nodes[0] if nodes else "",
        "end_node": nodes[-1] if nodes else "",
        "path_str": " -> ".join(nodes),
        "nodes": list(nodes),
        "transitions": _transitions_to_dicts(transitions),
    }


def _precompute_range_segment_counts(
    paths: Sequence[PathRecord],
    max_depth: int,
    max_segment_nodes: int,
) -> List[List[int]]:
    inf = 10**18
    max_segment_edges = max_segment_nodes - 1
    counts = [[inf for _ in range(max_depth + 1)] for _ in range(max_depth + 1)]
    for s in range(0, max_depth):
        for e in range(s + 1, max_depth + 1):
            if e - s > max_segment_edges:
                continue
            segs: set[SegmentKey] = set()
            for path in paths:
                last = len(path.nodes) - 1
                if last < s:
                    continue
                seg_end = min(e, last)
                seg_nodes = path.nodes[s : seg_end + 1]
                segs.add(_segment_key(seg_nodes))
            counts[s][e] = len(segs)
    return counts


def optimize_depth_cuts_for_k(
    paths: Sequence[PathRecord],
    k: int,
    max_segment_nodes: int,
) -> Dict | None:
    max_segment_edges = max_segment_nodes - 1
    if max_segment_edges <= 0:
        return None
    max_depth = max(len(p.nodes) - 1 for p in paths)
    if k < 1 or k > max_depth:
        return None
    min_k_for_width = int(math.ceil(float(max_depth) / float(max_segment_edges)))
    if k < min_k_for_width:
        return None

    inf = 10**18
    range_counts = _precompute_range_segment_counts(
        paths,
        max_depth,
        max_segment_nodes=max_segment_nodes,
    )
    dp = [[inf for _ in range(max_depth + 1)] for _ in range(k + 1)]
    parent = [[-1 for _ in range(max_depth + 1)] for _ in range(k + 1)]

    for d in range(1, max_depth + 1):
        if d <= max_segment_edges:
            dp[1][d] = range_counts[0][d]
            parent[1][d] = 0

    for g in range(2, k + 1):
        for d in range(g, max_depth + 1):
            best_cost = inf
            best_prev = -1
            prev_min = max(g - 1, d - max_segment_edges)
            for p in range(prev_min, d):
                if dp[g - 1][p] >= inf:
                    continue
                rc = range_counts[p][d]
                if rc >= inf:
                    continue
                total = dp[g - 1][p] + rc
                if total < best_cost:
                    best_cost = total
                    best_prev = p
            dp[g][d] = best_cost
            parent[g][d] = best_prev

    if dp[k][max_depth] >= inf:
        return None

    cuts = [max_depth]
    d = max_depth
    for g in range(k, 1, -1):
        p = parent[g][d]
        if p < 0:
            return None
        cuts.append(p)
        d = p
    cuts.append(0)
    cuts.reverse()
    if len(cuts) != k + 1 or cuts[0] != 0 or cuts[-1] != max_depth:
        return None
    return {
        "cut_points": cuts,
        "dp_cost": int(dp[k][max_depth]),
        "max_depth": max_depth,
        "max_segment_nodes": int(max_segment_nodes),
    }


def build_depth_subgraphs(
    paths: Sequence[PathRecord],
    cut_points: Sequence[int],
    max_segment_nodes: int,
) -> Tuple[Dict[int, Dict], List[List[Dict]]]:
    k = len(cut_points) - 1
    max_segment_edges = max_segment_nodes - 1
    subgraphs: Dict[int, Dict] = {}
    for sg_idx in range(k):
        layer_start = int(cut_points[sg_idx])
        layer_end = int(cut_points[sg_idx + 1])
        if layer_end - layer_start > max_segment_edges:
            raise AssertionError(
                "partition failed: subgraph width "
                f"{layer_end - layer_start + 1} nodes exceeds max_segment_nodes={max_segment_nodes}"
            )
        subgraphs[sg_idx] = {
            "subgraph_id": sg_idx + 1,
            "layer_start": layer_start,
            "layer_end": layer_end,
            "segments_usage": defaultdict(int),
            "segment_examples": {},
            "nodes": set(),
            "edges": set(),
            "segment_instance_count": 0,
        }

    path_segment_assignments: List[List[Dict]] = []
    for path_idx, path in enumerate(paths):
        per_path: List[Dict] = []
        last = len(path.nodes) - 1
        for sg_idx in range(k):
            sg = subgraphs[sg_idx]
            s = sg["layer_start"]
            e = sg["layer_end"]
            if last < s:
                break
            seg_end = min(e, last)
            if seg_end - s > max_segment_edges:
                raise AssertionError(
                    "partition failed: segment width "
                    f"{seg_end - s + 1} nodes exceeds max_segment_nodes={max_segment_nodes}"
                )
            seg_nodes = path.nodes[s : seg_end + 1]
            seg_trans = path.transitions[s:seg_end]
            seg_key = _segment_key(seg_nodes)
            sg["segments_usage"][seg_key] += 1
            if seg_key not in sg["segment_examples"]:
                sg["segment_examples"][seg_key] = tuple(seg_trans)
            sg["segment_instance_count"] += 1
            sg["nodes"].update(seg_nodes)
            sg["edges"].update(seg_trans)
            per_path.append(
                {
                    "subgraph_id": sg_idx + 1,
                    "layer_start": s,
                    "layer_end": e,
                    "actual_end_depth": seg_end,
                    "segment_nodes": list(seg_nodes),
                    "segment_path_str": " -> ".join(seg_nodes),
                    "segment_transitions": _transitions_to_dicts(seg_trans),
                    "segment_transition_count": len(seg_trans),
                }
            )
        if len(per_path) == 0:
            raise AssertionError(f"path {path_idx} has no segment assignment")
        path_segment_assignments.append(per_path)

    return subgraphs, path_segment_assignments


def reconstruct_path_from_segment_assignments(
    segments: Sequence[Dict],
) -> Tuple[Tuple[str, ...], Tuple[Transition, ...]]:
    if len(segments) == 0:
        raise AssertionError("partition failed: empty segment assignment")

    rebuilt_nodes: List[str] = []
    rebuilt_transitions: List[Transition] = []
    for idx, seg in enumerate(segments):
        snodes = [str(node) for node in seg.get("segment_nodes", [])]
        if len(snodes) == 0:
            raise AssertionError("partition failed: segment has no nodes")

        seg_transitions = [
            _transition_dict_to_tuple(t) for t in seg.get("segment_transitions", [])
        ]
        expected_transition_count = int(
            seg.get("segment_transition_count", len(seg_transitions))
        )
        if expected_transition_count != len(seg_transitions):
            raise AssertionError("partition failed: segment transition count mismatch")
        if len(seg_transitions) != max(0, len(snodes) - 1):
            raise AssertionError("partition failed: segment node/transition length mismatch")

        if idx == 0:
            rebuilt_nodes.extend(snodes)
        else:
            if len(rebuilt_nodes) == 0 or rebuilt_nodes[-1] != snodes[0]:
                raise AssertionError("partition failed: boundary node mismatch")
            rebuilt_nodes.extend(snodes[1:])
        rebuilt_transitions.extend(seg_transitions)

    return tuple(rebuilt_nodes), tuple(rebuilt_transitions)


def verify_depth_partition(paths: Sequence[PathRecord], path_segment_assignments: Sequence[Sequence[Dict]]) -> None:
    if len(paths) != len(path_segment_assignments):
        raise AssertionError("partition failed: path assignment size mismatch")

    for idx, path in enumerate(paths):
        segs = list(path_segment_assignments[idx])
        if len(segs) == 0:
            raise AssertionError("partition failed: empty segment assignment")
        for j in range(1, len(segs)):
            if segs[j]["subgraph_id"] <= segs[j - 1]["subgraph_id"]:
                raise AssertionError("partition failed: subgraph order is not strictly increasing")

        rebuilt_nodes, rebuilt_transitions = reconstruct_path_from_segment_assignments(segs)
        if tuple(rebuilt_nodes) != path.nodes:
            raise AssertionError("partition failed: reconstructed node sequence mismatch")
        if tuple(rebuilt_transitions) != path.transitions:
            raise AssertionError("partition failed: reconstructed transition sequence mismatch")


def compute_edge_duplication_from_depth_subgraphs(
    subgraphs: Dict[int, Dict],
    original_edges: set[Transition],
) -> float:
    if not original_edges:
        return 0.0
    total_subgraph_edges = float(sum(len(sg["edges"]) for sg in subgraphs.values()))
    return total_subgraph_edges / float(len(original_edges))


def compute_balance_from_depth_subgraphs(subgraphs: Dict[int, Dict]) -> float:
    sizes = np.asarray(
        [len(sg["segments_usage"]) for sg in subgraphs.values()],
        dtype=np.float64,
    )
    if sizes.size == 0:
        return 0.0
    mean_size = float(np.mean(sizes))
    if mean_size <= 0:
        return 0.0
    return float(np.std(sizes) / mean_size)


def evaluate_k_candidates(
    V: sp.csr_matrix,
    paths: Sequence[PathRecord],
    dag: ParserDAG,
    k_min: int,
    k_max: int,
    n_restarts: int,
    max_iter: int,
    tol: float,
    seed: int,
    weights: Tuple[float, float, float],
    max_segment_nodes: int,
) -> Tuple[int, Dict[int, Dict]]:
    max_segment_edges = max_segment_nodes - 1
    if max_segment_edges <= 0:
        raise ValueError("max_segment_nodes must be >= 2")
    w1, w2, w3 = weights
    candidates: Dict[int, Dict] = {}
    max_depth = max(len(p.nodes) - 1 for p in paths)
    min_k_for_width = int(math.ceil(float(max_depth) / float(max_segment_edges)))
    max_feasible_k = min(k_max, max_depth, min(V.shape))
    k_start = max(k_min, min_k_for_width)
    if k_start > max_feasible_k:
        raise RuntimeError(
            "no valid k candidates after NMF decomposition: "
            f"max_depth={max_depth}, max_segment_nodes={max_segment_nodes}, "
            f"requires k>={min_k_for_width}, but k_max={k_max}, matrix_min_dim={min(V.shape)}"
        )

    for k in range(k_start, max_feasible_k + 1):
        try:
            W, H, e_recon = nmf_decompose(
                V=V,
                k=k,
                n_restarts=n_restarts,
                max_iter=max_iter,
                tol=tol,
                seed=seed,
            )
        except Exception as exc:
            candidates[k] = {"error": str(exc)}
            continue

        plan = optimize_depth_cuts_for_k(
            paths,
            k,
            max_segment_nodes=max_segment_nodes,
        )
        if plan is None:
            candidates[k] = {
                "error": (
                    f"no valid depth-cut plan for k={k} under "
                    f"max_segment_nodes={max_segment_nodes}"
                )
            }
            continue
        cut_points = plan["cut_points"]
        subgraphs, path_segment_assignments = build_depth_subgraphs(
            paths,
            cut_points,
            max_segment_nodes=max_segment_nodes,
        )
        actual_k = len([sg for sg in subgraphs.values() if len(sg["segments_usage"]) > 0])
        if actual_k < k_min:
            candidates[k] = {"error": f"actual_k={actual_k} < {k_min}"}
            continue

        verify_depth_partition(paths, path_segment_assignments)

        e_dup = compute_edge_duplication_from_depth_subgraphs(subgraphs, dag.edges)
        e_bal = compute_balance_from_depth_subgraphs(subgraphs)
        candidates[k] = {
            "requested_k": k,
            "actual_k": actual_k,
            "cut_points": cut_points,
            "subgraphs": subgraphs,
            "path_segment_assignments": path_segment_assignments,
            "e_recon": float(e_recon),
            "e_dup": float(e_dup),
            "e_bal": float(e_bal),
            "W_shape": list(W.shape),
            "H_shape": list(H.shape),
        }

    valid_ks = sorted(k for k, v in candidates.items() if "error" not in v)
    if not valid_ks:
        raise RuntimeError("no valid k candidates after NMF decomposition")

    recon_norm = min_max_normalize([candidates[k]["e_recon"] for k in valid_ks])
    dup_norm = min_max_normalize([candidates[k]["e_dup"] for k in valid_ks])
    bal_norm = min_max_normalize([candidates[k]["e_bal"] for k in valid_ks])

    for idx, k in enumerate(valid_ks):
        score = w1 * recon_norm[idx] + w2 * dup_norm[idx] + w3 * bal_norm[idx]
        candidates[k]["score"] = float(score)
        candidates[k]["norm"] = {
            "e_recon_norm": float(recon_norm[idx]),
            "e_dup_norm": float(dup_norm[idx]),
            "e_bal_norm": float(bal_norm[idx]),
        }

    best_k = min(valid_ks, key=lambda x: (candidates[x]["score"], x))
    return best_k, candidates


def path_to_dict(path: PathRecord) -> Dict:
    return {
        "nodes": list(path.nodes),
        "depth_nodes": len(path.nodes),
        "depth_edges": max(0, len(path.nodes) - 1),
        "path_str": " -> ".join(path.nodes),
        "transitions": _transitions_to_dicts(path.transitions),
    }


def serialize_depth_subgraphs(subgraphs: Dict[int, Dict]) -> List[Dict]:
    out: List[Dict] = []
    for label in sorted(subgraphs.keys()):
        sg = subgraphs[label]
        edge_list = sorted(sg["edges"], key=lambda x: (x[0], x[1], x[2]))
        segment_keys = sorted(
            sg["segments_usage"].keys(),
            key=lambda x: (len(x[0]), " -> ".join(x[0])),
        )
        segment_id_map = {
            k: f"sg{sg['subgraph_id']}_seg_{idx+1:03d}" for idx, k in enumerate(segment_keys)
        }
        segments = [
            _segment_to_dict(
                segment_id_map[k],
                k,
                sg["segments_usage"][k],
                sg["segment_examples"].get(k, ()),
            )
            for k in segment_keys
        ]
        out.append(
            {
                "subgraph_id": int(sg["subgraph_id"]),
                "layer_start": int(sg["layer_start"]),
                "layer_end": int(sg["layer_end"]),
                "num_unique_segments": len(segment_keys),
                "num_segment_instances": int(sg["segment_instance_count"]),
                "num_nodes": len(sg["nodes"]),
                "num_edges": len(edge_list),
                "nodes": sorted(sg["nodes"]),
                "edges": [
                    {"src": src, "dst": dst, "condition": cond}
                    for src, dst, cond in edge_list
                ],
                "segments": segments,
            }
        )
    return out


def _escape_md_cell(value: object) -> str:
    text = str(value)
    text = text.replace("|", "\\|")
    text = text.replace("\r\n", "<br>").replace("\n", "<br>")
    return text


def _format_transition_chain(transitions: Sequence[Dict]) -> str:
    if not transitions:
        return "(terminal node only)"
    parts: List[str] = []
    for transition in transitions:
        src = str(transition.get("src", ""))
        dst = str(transition.get("dst", ""))
        cond = str(transition.get("condition", ""))
        cond_label = cond if cond else "always"
        parts.append(f"{src} -[{cond_label}]-> {dst}")
    return " | ".join(parts)


def build_serialized_path_verification_report(parser_result: Dict) -> Dict:
    records: List[Dict] = []
    for path_entry in parser_result.get("paths", []):
        path_index = int(path_entry.get("path_index", len(records)))
        original_path = path_entry.get("original_path", {})
        original_nodes = tuple(str(node) for node in original_path.get("nodes", []))
        original_transitions = tuple(
            _transition_dict_to_tuple(t) for t in original_path.get("transitions", [])
        )
        segments = list(path_entry.get("segments", []))
        order_ok = all(
            segments[j]["subgraph_id"] > segments[j - 1]["subgraph_id"]
            for j in range(1, len(segments))
        )

        rebuilt_nodes: Tuple[str, ...] = tuple()
        rebuilt_transitions: Tuple[Transition, ...] = tuple()
        error = ""
        try:
            if not order_ok:
                raise AssertionError("subgraph order is not strictly increasing")
            rebuilt_nodes, rebuilt_transitions = reconstruct_path_from_segment_assignments(segments)
        except AssertionError as exc:
            error = str(exc)

        node_match = rebuilt_nodes == original_nodes
        transition_match = rebuilt_transitions == original_transitions
        if not error and not node_match:
            error = "reconstructed node sequence mismatch"
        if not error and not transition_match:
            error = "reconstructed transition sequence mismatch"

        records.append(
            {
                "path_index": path_index,
                "status": "PASS" if not error and node_match and transition_match else "FAIL",
                "segment_count": len(segments),
                "node_match": node_match,
                "transition_match": transition_match,
                "original_path_str": str(original_path.get("path_str", "")),
                "reconstructed_path_str": " -> ".join(rebuilt_nodes) if rebuilt_nodes else "",
                "segment_chain": [
                    f"SG{int(seg['subgraph_id'])}: {str(seg.get('segment_path_str', ''))}"
                    for seg in segments
                ],
                "error": error,
            }
        )

    failed = [record for record in records if record["status"] != "PASS"]
    return {
        "verified_path_count": len(records),
        "passed_path_count": len(records) - len(failed),
        "failed_path_count": len(failed),
        "all_paths_reconstructed": len(failed) == 0,
        "failed_path_indexes": [record["path_index"] for record in failed],
        "records": records,
    }


def render_partition_markdown(result: Dict) -> str:
    source_json = str(result.get("source_json", ""))
    config = result.get("config", {})
    lines: List[str] = [
        f"# {Path(source_json).name} NMF Partition Report",
        "",
        "## Source",
        f"- Source JSON: `{source_json}`",
        f"- Created at: `{result.get('created_at', '')}`",
        f"- Algorithm: `{result.get('algorithm', '')}`",
        f"- Parser count: `{result.get('num_parsers', 0)}`",
        f"- k range: `{config.get('k_min', '')}` to `{config.get('k_max', '')}`",
        f"- NMF restarts: `{config.get('n_restarts', '')}`",
        f"- Max paths: `{config.get('max_paths', '')}`",
        f"- Max segment nodes (hard constraint): `{config.get('max_segment_nodes', '')}`",
        f"- Max iter: `{config.get('max_iter', '')}`",
        f"- Tol: `{config.get('tol', '')}`",
        f"- Seed: `{config.get('seed', '')}`",
    ]

    weights = config.get("weights", {})
    if weights:
        lines.append(
            f"- Weights: `w1={weights.get('w1', '')}, w2={weights.get('w2', '')}, w3={weights.get('w3', '')}`"
        )

    for parser_idx, parser_result in enumerate(result.get("parser_results", []), start=1):
        parser_name = str(parser_result.get("parser_name", f"parser_{parser_idx}"))
        lines.extend(
            [
                "",
                f"## Parser {parser_idx}: `{parser_name}`",
                f"- Status: `{parser_result.get('status', 'unknown')}`",
            ]
        )

        if parser_result.get("status") != "ok":
            if "reason" in parser_result:
                lines.append(f"- Reason: `{parser_result.get('reason', '')}`")
            continue

        best_metrics = parser_result.get("best_metrics", {})
        verification = parser_result.get("path_verification") or build_serialized_path_verification_report(parser_result)
        lines.extend(
            [
                "",
                "### Summary",
                f"- Start state: `{parser_result.get('start_state', '')}`",
                f"- Nodes: `{parser_result.get('num_nodes', 0)}`",
                f"- Edges: `{parser_result.get('num_edges', 0)}`",
                f"- Original path count: `{parser_result.get('original_path_count', 0)}`",
                f"- Unique node path count: `{parser_result.get('unique_node_path_count', 0)}`",
                f"- Duplicate node path count removed: `{parser_result.get('duplicate_node_path_count', 0)}`",
                f"- Path basis: `{parser_result.get('path_basis', 'path_instances')}`",
                f"- Path truncated: `{parser_result.get('path_truncated', False)}`",
                f"- Total unique segments: `{parser_result.get('total_unique_segment_count', 0)}`",
                f"- Total segment instances: `{parser_result.get('total_segment_instance_count', 0)}`",
                f"- Virtual node count: `{parser_result.get('virtual_node_count', 0)}`",
                f"- Matrix shape: `{parser_result.get('matrix_shape', [])}`",
                f"- Matrix nnz: `{parser_result.get('matrix_nnz', 0)}`",
                f"- Matrix density: `{parser_result.get('matrix_density', 0.0)}`",
                f"- Best requested k: `{parser_result.get('best_requested_k', 0)}`",
                f"- Best actual k: `{parser_result.get('best_actual_k', 0)}`",
                f"- Best cut points: `{parser_result.get('best_cut_points', [])}`",
                f"- Best score: `{best_metrics.get('score', 0.0)}`",
                f"- Best e_recon: `{best_metrics.get('e_recon', 0.0)}`",
                f"- Best e_dup: `{best_metrics.get('e_dup', 0.0)}`",
                f"- Best e_bal: `{best_metrics.get('e_bal', 0.0)}`",
            ]
        )

        lines.extend(
            [
                "",
                "### Reconstruction Verification",
                f"- All paths reconstructed: `{verification['all_paths_reconstructed']}`",
                f"- Verified paths: `{verification['verified_path_count']}`",
                f"- Passed paths: `{verification['passed_path_count']}`",
                f"- Failed paths: `{verification['failed_path_count']}`",
            ]
        )
        if verification["failed_path_indexes"]:
            failed_indexes = ", ".join(str(idx) for idx in verification["failed_path_indexes"])
            lines.append(f"- Failed path indexes: `{failed_indexes}`")

        lines.extend(["", "### Subgraphs"])
        for subgraph in parser_result.get("subgraphs", []):
            lines.extend(
                [
                    "",
                    f"#### Subgraph {subgraph.get('subgraph_id', 0)} [{subgraph.get('layer_start', 0)}, {subgraph.get('layer_end', 0)}]",
                    f"- Unique segments: `{subgraph.get('num_unique_segments', 0)}`",
                    f"- Segment instances: `{subgraph.get('num_segment_instances', 0)}`",
                    f"- Nodes: `{subgraph.get('num_nodes', 0)}`",
                    f"- Edges: `{subgraph.get('num_edges', 0)}`",
                    "",
                    "| Segment ID | Usage | Depth Nodes | Depth Edges | Start | End | Path | Transitions |",
                    "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
                ]
            )
            for segment in subgraph.get("segments", []):
                lines.append(
                    "| "
                    f"{_escape_md_cell(segment.get('segment_id', ''))} | "
                    f"{_escape_md_cell(segment.get('usage_count', 0))} | "
                    f"{_escape_md_cell(segment.get('depth_nodes', 0))} | "
                    f"{_escape_md_cell(segment.get('depth_edges', 0))} | "
                    f"{_escape_md_cell(segment.get('start_node', ''))} | "
                    f"{_escape_md_cell(segment.get('end_node', ''))} | "
                    f"{_escape_md_cell(segment.get('path_str', ''))} | "
                    f"{_escape_md_cell(_format_transition_chain(segment.get('transitions', [])))} |"
                )

        lines.extend(
            [
                "",
                "### Path Reconstruction Details",
                "| Path Index | Status | Node Match | Transition Match | Segment Count | Original Path | Reconstructed Path | Segment Chain | Error |",
                "| ---: | --- | --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for record in verification["records"]:
            segment_chain = "<br>".join(_escape_md_cell(item) for item in record["segment_chain"])
            lines.append(
                "| "
                f"{_escape_md_cell(record['path_index'])} | "
                f"{_escape_md_cell(record['status'])} | "
                f"{_escape_md_cell(record['node_match'])} | "
                f"{_escape_md_cell(record['transition_match'])} | "
                f"{_escape_md_cell(record['segment_count'])} | "
                f"{_escape_md_cell(record['original_path_str'])} | "
                f"{_escape_md_cell(record['reconstructed_path_str'])} | "
                f"{segment_chain} | "
                f"{_escape_md_cell(record['error'])} |"
            )

    return "\n".join(lines).rstrip() + "\n"


def process_parser(
    dag: ParserDAG,
    k_min: int,
    k_max: int,
    n_restarts: int,
    max_paths: int,
    max_iter: int,
    tol: float,
    seed: int,
    weights: Tuple[float, float, float],
    max_segment_nodes: int,
) -> Dict:
    path_limit = max_paths if max_paths and max_paths > 0 else None
    paths, truncated = enumerate_paths(dag, max_paths=path_limit)
    if truncated:
        raise RuntimeError(
            "full path enumeration truncated; cannot guarantee 100% unique-node-path reconstruction. "
            f"Increase --max-paths (current={max_paths}) or set --max-paths 0 for no limit."
        )

    unique_paths, duplicate_node_path_count = deduplicate_paths_by_nodes(paths)
    if len(unique_paths) < k_min:
        return {
            "parser_name": dag.parser_name,
            "status": "skipped",
            "reason": f"unique_node_paths={len(unique_paths)} < k_min={k_min}",
            "path_truncated": truncated,
            "original_path_count": len(paths),
            "unique_node_path_count": len(unique_paths),
        }

    V, vnode_index = build_virtual_node_matrix(unique_paths)
    best_k, candidates = evaluate_k_candidates(
        V=V,
        paths=unique_paths,
        dag=dag,
        k_min=k_min,
        k_max=k_max,
        n_restarts=n_restarts,
        max_iter=max_iter,
        tol=tol,
        seed=seed,
        weights=weights,
        max_segment_nodes=max_segment_nodes,
    )

    best = candidates[best_k]
    subgraphs = best["subgraphs"]
    serialized_subgraphs = serialize_depth_subgraphs(subgraphs)

    candidate_metrics = []
    for k in sorted(candidates.keys()):
        c = candidates[k]
        if "error" in c:
            candidate_metrics.append({"k": k, "error": c["error"]})
        else:
            candidate_metrics.append(
                {
                    "k": k,
                    "requested_k": c["requested_k"],
                    "actual_k": c["actual_k"],
                    "cut_points": c["cut_points"],
                    "e_recon": c["e_recon"],
                    "e_dup": c["e_dup"],
                    "e_bal": c["e_bal"],
                    "score": c["score"],
                    "norm": c["norm"],
                }
            )

    total_unique_segments = int(sum(s["num_unique_segments"] for s in serialized_subgraphs))
    total_segment_instances = int(sum(s["num_segment_instances"] for s in serialized_subgraphs))
    density = float(V.nnz) / float(V.shape[0] * V.shape[1]) if V.shape[0] * V.shape[1] > 0 else 0.0
    full_paths = [path_to_dict(p) for p in unique_paths]
    path_segment_assignments = [
        {
            "path_index": idx,
            "original_path": full_paths[idx],
            "segments": segs,
        }
        for idx, segs in enumerate(best["path_segment_assignments"])
    ]
    verification = build_serialized_path_verification_report(
        {
            "paths": path_segment_assignments,
        }
    )
    if not verification["all_paths_reconstructed"]:
        raise RuntimeError(
            "100% unique-node-path reconstruction verification failed: "
            f"failed_path_count={verification['failed_path_count']}"
        )

    return {
        "parser_name": dag.parser_name,
        "status": "ok",
        "path_truncated": truncated,
        "start_state": dag.start_state,
        "num_nodes": len(dag.nodes),
        "num_edges": len(dag.edges),
        "original_path_count": len(paths),
        "unique_node_path_count": len(unique_paths),
        "duplicate_node_path_count": duplicate_node_path_count,
        "total_unique_segment_count": total_unique_segments,
        "total_segment_instance_count": total_segment_instances,
        "virtual_node_count": len(vnode_index),
        "matrix_shape": list(V.shape),
        "matrix_nnz": int(V.nnz),
        "matrix_density": density,
        "best_requested_k": int(best_k),
        "best_actual_k": int(best["actual_k"]),
        "best_cut_points": best["cut_points"],
        "best_metrics": {
            "score": float(best["score"]),
            "e_recon": float(best["e_recon"]),
            "e_dup": float(best["e_dup"]),
            "e_bal": float(best["e_bal"]),
            "norm": best["norm"],
        },
        "weights": {"w1": weights[0], "w2": weights[1], "w3": weights[2]},
        "candidates": candidate_metrics,
        "subgraphs": serialized_subgraphs,
        "paths": path_segment_assignments,
        "path_verification": verification,
        "path_basis": "unique_node_paths",
    }


def process_file(
    input_file: Path,
    output_dir: Path,
    k_min: int,
    k_max: int,
    n_restarts: int,
    max_paths: int,
    max_iter: int,
    tol: float,
    seed: int,
    weights: Tuple[float, float, float],
    max_segment_nodes: int,
    write_markdown: bool,
) -> Tuple[Path, Path | None]:
    payload = json.loads(input_file.read_text(encoding="utf-8"))
    dags = build_dags_from_json(payload)

    parser_results = []
    for dag in dags:
        parser_results.append(
            process_parser(
                dag=dag,
                k_min=k_min,
                k_max=k_max,
                n_restarts=n_restarts,
                max_paths=max_paths,
                max_iter=max_iter,
                tol=tol,
                seed=seed,
                weights=weights,
                max_segment_nodes=max_segment_nodes,
            )
        )

    output = {
        "source_json": str(input_file),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "algorithm": "NMF-DAG-Partition",
        "config": {
            "k_min": k_min,
            "k_max": k_max,
            "n_restarts": n_restarts,
            "max_paths": max_paths,
            "max_iter": max_iter,
            "tol": tol,
            "seed": seed,
            "max_segment_nodes": max_segment_nodes,
            "weights": {"w1": weights[0], "w2": weights[1], "w3": weights[2]},
        },
        "num_parsers": len(parser_results),
        "parser_results": parser_results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{input_file.stem}.nmf_partition_result.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path: Path | None = None
    if write_markdown:
        markdown_path = output_dir / f"{input_file.stem}.nmf_partition_result.md"
        markdown_path.write_text(render_partition_markdown(output), encoding="utf-8")
    return out_path, markdown_path


def discover_json_files(input_dir: Path, pattern: str) -> List[Path]:
    return sorted(p for p in input_dir.glob(pattern) if p.is_file())


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="NMF-based DAG path partition for P4 parser JSON files.")
    ap.add_argument("--input-dir", type=Path, default=SCRIPT_DIR, help="Directory containing source JSON files.")
    ap.add_argument("--input-file", type=Path, default=None, help="Single JSON file to process.")
    ap.add_argument("--pattern", type=str, default="*.p4.json", help="Glob pattern when using --input-dir.")
    ap.add_argument("--output-dir", type=Path, default=SCRIPT_DIR, help="Directory to write result JSON files.")
    ap.add_argument("--k-min", type=int, default=2)
    ap.add_argument("--k-max", type=int, default=10)
    ap.add_argument("--n-restarts", type=int, default=10)
    ap.add_argument(
        "--max-paths",
        type=int,
        default=0,
        help="Maximum complete paths to enumerate before deduplication. Use 0 for no limit.",
    )
    ap.add_argument(
        "--max-segment-nodes",
        type=int,
        default=HARD_MAX_SEGMENT_NODES,
        help="Hard constraint: each subgraph segment depth_nodes must be <= this value.",
    )
    ap.add_argument("--max-iter", type=int, default=500)
    ap.add_argument("--tol", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--w1", type=float, default=0.3, help="Weight for normalized reconstruction error.")
    ap.add_argument("--w2", type=float, default=0.5, help="Weight for normalized edge duplication.")
    ap.add_argument("--w3", type=float, default=0.2, help="Weight for normalized balance.")
    ap.add_argument(
        "--write-markdown",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also write a Markdown report with all subgraph segments and path reconstruction verification.",
    )
    ap.add_argument(
        "--summary-name",
        type=str,
        default="nmf_partition_batch_summary.json",
        help="Batch summary output filename in output-dir.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    weights = (args.w1, args.w2, args.w3)

    if args.input_file is not None:
        input_files = [args.input_file]
    else:
        input_files = discover_json_files(args.input_dir, args.pattern)

    if not input_files:
        print(f"[ERROR] No input JSON files found. input_dir={args.input_dir} pattern={args.pattern}")
        return 1

    summary_rows = []
    for input_file in input_files:
        try:
            out_path, markdown_path = process_file(
                input_file=input_file,
                output_dir=args.output_dir,
                k_min=args.k_min,
                k_max=args.k_max,
                n_restarts=args.n_restarts,
                max_paths=args.max_paths,
                max_iter=args.max_iter,
                tol=args.tol,
                seed=args.seed,
                weights=weights,
                max_segment_nodes=args.max_segment_nodes,
                write_markdown=args.write_markdown,
            )
            row = {"input_file": str(input_file), "status": "ok", "output_file": str(out_path)}
            if markdown_path is not None:
                row["markdown_file"] = str(markdown_path)
                print(f"[OK] {input_file.name} -> {out_path.name}, {markdown_path.name}")
            else:
                print(f"[OK] {input_file.name} -> {out_path.name}")
            summary_rows.append(row)
        except Exception as exc:
            summary_rows.append({"input_file": str(input_file), "status": "error", "error": str(exc)})
            print(f"[ERROR] {input_file.name}: {exc}")

    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_count": len(input_files),
        "ok_count": sum(1 for r in summary_rows if r["status"] == "ok"),
        "error_count": sum(1 for r in summary_rows if r["status"] != "ok"),
        "rows": summary_rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / args.summary_name
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SUMMARY] {summary_path}")
    return 0 if summary["error_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

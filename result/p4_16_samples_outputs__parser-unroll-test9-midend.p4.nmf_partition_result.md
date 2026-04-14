# p4_16_samples_outputs__parser-unroll-test9-midend.p4.json NMF Partition Report

## Source
- Source JSON: `C:\Users\DELL\Desktop\666\SpMM_Parser-master\nmf vs layer\p4_16_samples_outputs__parser-unroll-test9-midend.p4.json`
- Created at: `2026-04-13T15:22:24`
- Algorithm: `NMF-DAG-Partition`
- Parser count: `1`
- k range: `2` to `10`
- NMF restarts: `10`
- Max paths: `0`
- Max segment nodes (hard constraint): `6`
- Max iter: `500`
- Tol: `0.0001`
- Seed: `0`
- Weights: `w1=0.3, w2=0.5, w3=0.2`

## Parser 1: `p`
- Status: `ok`

### Summary
- Start state: `start`
- Nodes: `18`
- Edges: `31`
- Original path count: `17`
- Unique node path count: `17`
- Duplicate node path count removed: `0`
- Path basis: `unique_node_paths`
- Path truncated: `False`
- Total unique segments: `21`
- Total segment instances: `33`
- Virtual node count: `30`
- Matrix shape: `[17, 30]`
- Matrix nnz: `103`
- Matrix density: `0.2019607843137255`
- Best requested k: `2`
- Best actual k: `2`
- Best cut points: `[0, 3, 8]`
- Best score: `0.3`
- Best e_recon: `0.5720288813522117`
- Best e_dup: `0.9354838709677419`
- Best e_bal: `0.3333333333333333`

### Reconstruction Verification
- All paths reconstructed: `True`
- Verified paths: `17`
- Passed paths: `17`
- Failed paths: `0`

### Subgraphs

#### Subgraph 1 [0, 3]
- Unique segments: `7`
- Segment instances: `17`
- Nodes: `10`
- Edges: `11`

| Segment ID | Usage | Depth Nodes | Depth Edges | Start | End | Path | Transitions |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| sg1_seg_001 | 10 | 4 | 3 | start | start_loops1 | start -> start_loops -> mixed_finite_loop -> start_loops1 | start -[always]-> start_loops \| start_loops -[8w0]-> mixed_finite_loop \| mixed_finite_loop -[8w1]-> start_loops1 |
| sg1_seg_002 | 1 | 4 | 3 | start | accept | start -> start_loops -> mixed_finite_loop -> accept | start -[always]-> start_loops \| start_loops -[8w0]-> mixed_finite_loop \| mixed_finite_loop -[8w2]-> accept |
| sg1_seg_003 | 1 | 4 | 3 | start | noMatch | start -> start_loops -> mixed_finite_loop -> noMatch | start -[always]-> start_loops \| start_loops -[8w0]-> mixed_finite_loop \| mixed_finite_loop -[default]-> noMatch |
| sg1_seg_004 | 1 | 4 | 3 | start | accept | start -> start_loops -> infinite_loop -> accept | start -[always]-> start_loops \| start_loops -[8w2]-> infinite_loop \| infinite_loop -[8w3]-> accept |
| sg1_seg_005 | 1 | 4 | 3 | start | accept | start -> start_loops -> finite_loop -> accept | start -[always]-> start_loops \| start_loops -[8w3]-> finite_loop \| finite_loop -[8w2]-> accept |
| sg1_seg_006 | 2 | 4 | 3 | start | finite_loop1 | start -> start_loops -> finite_loop -> finite_loop1 | start -[always]-> start_loops \| start_loops -[8w3]-> finite_loop \| finite_loop -[default]-> finite_loop1 |
| sg1_seg_007 | 1 | 3 | 2 | start | reject | start -> start_loops -> reject | start -[always]-> start_loops \| start_loops -[default]-> reject |

#### Subgraph 2 [3, 8]
- Unique segments: `14`
- Segment instances: `16`
- Nodes: `11`
- Edges: `18`

| Segment ID | Usage | Depth Nodes | Depth Edges | Start | End | Path | Transitions |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| sg2_seg_001 | 3 | 1 | 0 | accept | accept | accept | (terminal node only) |
| sg2_seg_002 | 1 | 2 | 1 | noMatch | reject | noMatch -> reject | noMatch -[always]-> reject |
| sg2_seg_003 | 1 | 2 | 1 | finite_loop1 | accept | finite_loop1 -> accept | finite_loop1 -[8w2]-> accept |
| sg2_seg_004 | 1 | 4 | 3 | finite_loop1 | reject | finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | finite_loop1 -[default]-> finite_loop2 \| finite_loop2 -[always]-> stateOutOfBound \| stateOutOfBound -[always]-> reject |
| sg2_seg_005 | 1 | 6 | 5 | start_loops1 | reject | start_loops1 -> mixed_finite_loop1 -> start_loops2 -> mixed_finite_loop2 -> stateOutOfBound -> reject | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[8w1]-> start_loops2 \| start_loops2 -[8w0]-> mixed_finite_loop2 \| mixed_finite_loop2 -[always]-> stateOutOfBound \| stateOutOfBound -[always]-> reject |
| sg2_seg_006 | 1 | 5 | 4 | start_loops1 | accept | start_loops1 -> mixed_finite_loop1 -> start_loops2 -> infinite_loop -> accept | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[8w1]-> start_loops2 \| start_loops2 -[8w2]-> infinite_loop \| infinite_loop -[8w3]-> accept |
| sg2_seg_007 | 1 | 6 | 5 | start_loops1 | reject | start_loops1 -> mixed_finite_loop1 -> start_loops2 -> finite_loop2 -> stateOutOfBound -> reject | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[8w1]-> start_loops2 \| start_loops2 -[8w3]-> finite_loop2 \| finite_loop2 -[always]-> stateOutOfBound \| stateOutOfBound -[always]-> reject |
| sg2_seg_008 | 1 | 4 | 3 | start_loops1 | reject | start_loops1 -> mixed_finite_loop1 -> start_loops2 -> reject | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[8w1]-> start_loops2 \| start_loops2 -[default]-> reject |
| sg2_seg_009 | 1 | 3 | 2 | start_loops1 | accept | start_loops1 -> mixed_finite_loop1 -> accept | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[8w2]-> accept |
| sg2_seg_010 | 1 | 4 | 3 | start_loops1 | reject | start_loops1 -> mixed_finite_loop1 -> noMatch -> reject | start_loops1 -[8w0]-> mixed_finite_loop1 \| mixed_finite_loop1 -[default]-> noMatch \| noMatch -[always]-> reject |
| sg2_seg_011 | 1 | 3 | 2 | start_loops1 | accept | start_loops1 -> infinite_loop -> accept | start_loops1 -[8w2]-> infinite_loop \| infinite_loop -[8w3]-> accept |
| sg2_seg_012 | 1 | 3 | 2 | start_loops1 | accept | start_loops1 -> finite_loop1 -> accept | start_loops1 -[8w3]-> finite_loop1 \| finite_loop1 -[8w2]-> accept |
| sg2_seg_013 | 1 | 5 | 4 | start_loops1 | reject | start_loops1 -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | start_loops1 -[8w3]-> finite_loop1 \| finite_loop1 -[default]-> finite_loop2 \| finite_loop2 -[always]-> stateOutOfBound \| stateOutOfBound -[always]-> reject |
| sg2_seg_014 | 1 | 2 | 1 | start_loops1 | reject | start_loops1 -> reject | start_loops1 -[default]-> reject |

### Path Reconstruction Details
| Path Index | Status | Node Match | Transition Match | Segment Count | Original Path | Reconstructed Path | Segment Chain | Error |
| ---: | --- | --- | --- | ---: | --- | --- | --- | --- |
| 0 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> mixed_finite_loop2 -> stateOutOfBound -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> mixed_finite_loop2 -> stateOutOfBound -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> start_loops2 -> mixed_finite_loop2 -> stateOutOfBound -> reject |  |
| 1 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> infinite_loop -> accept | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> infinite_loop -> accept | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> start_loops2 -> infinite_loop -> accept |  |
| 2 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> finite_loop2 -> stateOutOfBound -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> finite_loop2 -> stateOutOfBound -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> start_loops2 -> finite_loop2 -> stateOutOfBound -> reject |  |
| 3 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> start_loops2 -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> start_loops2 -> reject |  |
| 4 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> accept | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> accept | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> accept |  |
| 5 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> noMatch -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> mixed_finite_loop1 -> noMatch -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> mixed_finite_loop1 -> noMatch -> reject |  |
| 6 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> infinite_loop -> accept | start -> start_loops -> mixed_finite_loop -> start_loops1 -> infinite_loop -> accept | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> infinite_loop -> accept |  |
| 7 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> finite_loop1 -> accept | start -> start_loops -> mixed_finite_loop -> start_loops1 -> finite_loop1 -> accept | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> finite_loop1 -> accept |  |
| 8 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject |  |
| 9 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> start_loops1 -> reject | start -> start_loops -> mixed_finite_loop -> start_loops1 -> reject | SG1: start -> start_loops -> mixed_finite_loop -> start_loops1<br>SG2: start_loops1 -> reject |  |
| 10 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> accept | start -> start_loops -> mixed_finite_loop -> accept | SG1: start -> start_loops -> mixed_finite_loop -> accept<br>SG2: accept |  |
| 11 | PASS | True | True | 2 | start -> start_loops -> mixed_finite_loop -> noMatch -> reject | start -> start_loops -> mixed_finite_loop -> noMatch -> reject | SG1: start -> start_loops -> mixed_finite_loop -> noMatch<br>SG2: noMatch -> reject |  |
| 12 | PASS | True | True | 2 | start -> start_loops -> infinite_loop -> accept | start -> start_loops -> infinite_loop -> accept | SG1: start -> start_loops -> infinite_loop -> accept<br>SG2: accept |  |
| 13 | PASS | True | True | 2 | start -> start_loops -> finite_loop -> accept | start -> start_loops -> finite_loop -> accept | SG1: start -> start_loops -> finite_loop -> accept<br>SG2: accept |  |
| 14 | PASS | True | True | 2 | start -> start_loops -> finite_loop -> finite_loop1 -> accept | start -> start_loops -> finite_loop -> finite_loop1 -> accept | SG1: start -> start_loops -> finite_loop -> finite_loop1<br>SG2: finite_loop1 -> accept |  |
| 15 | PASS | True | True | 2 | start -> start_loops -> finite_loop -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | start -> start_loops -> finite_loop -> finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject | SG1: start -> start_loops -> finite_loop -> finite_loop1<br>SG2: finite_loop1 -> finite_loop2 -> stateOutOfBound -> reject |  |
| 16 | PASS | True | True | 1 | start -> start_loops -> reject | start -> start_loops -> reject | SG1: start -> start_loops -> reject |  |

# Actual R/NbClust merge-strength clustering

- Points: 84 (SJ02 is excluded by the current formal input set).
- Features: avg_S0_S1, avg_S1_S2, avg_S2_S3; z-score standardized; Euclidean distance; candidate k=2..6.
- R: 4.4.0; NbClust: 3.0.1; seed: 20261111.
- The map uses Ward.D2 labels selected by NbClust majority rule; k-means is included as a method sensitivity check.

## Majority votes

| Method | Selected k | Votes for selected k | Valid index votes | Vote breakdown (k:votes) |
|---|---:|---:|---:|---|
| ward.D2 | 3 | 15 | 23 | 2:1, 3:15, 4:4, 5:1, 6:2 |
| kmeans | 3 | 12 | 23 | 2:5, 3:12, 4:5, 5:1, 6:0 |

## Ward.D2 cluster centers

| Display cluster | Points | Mean S0-S1 | Mean S1-S2 | Mean S2-S3 |
|---|---:|---:|---:|---:|
| C1 低强度型 | 24 | 0.096 | 0.036 | 0.114 |
| C2 歌模合并主导型 | 51 | 0.193 | 0.066 | 0.548 |
| C3 歌麻合并主导型 | 9 | 0.100 | 0.553 | 0.112 |

## Comparison with the current Python-selected k-means k=3

- Adjusted Rand index (R Ward.D2 vs current): 0.915.
- Adjusted Rand index (R k-means vs current): 1.000.
- Ward.D2 vs current cluster cross-tab after aligning semantic labels:

```text
                   r_ward_d2
current_kmeans_k3   C1 低强度型 C2 歌模合并主导型 C3 歌麻合并主导型
  C1 低强度型                24                 2                 0
  C2 歌模合并主导型           0                49                 0
  C3 歌麻合并主导型           0                 0                 9
```

- Points whose Ward.D2 partition differs from current: 2 / 84.
- Points moved to a different group: 江阴城区澄江镇、吴江芦墟

Full point assignments, index votes, and NbClust console output are saved alongside this report.

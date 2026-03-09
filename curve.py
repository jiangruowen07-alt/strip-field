"""
曲线插值：Catmull-Rom 样条、弧长均匀采样
"""

import math

from utils import lerp


def catmull_rom_point(p0, p1, p2, p3, t):
    """Catmull-Rom 样条：t∈[0,1] 为 p1 到 p2 之间的插值"""
    t2, t3 = t * t, t * t * t
    x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t +
               (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
               (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t +
               (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
               (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return (x, y)


def sample_curve(points, num_samples=80):
    """将控制点通过 Catmull-Rom 样条采样为平滑曲线点"""
    if not points:
        return []
    if len(points) == 1:
        return [points[0]]
    if len(points) == 2:
        return [(lerp(points[0][0], points[1][0], i / max(num_samples - 1, 1)),
                 lerp(points[0][1], points[1][1], i / max(num_samples - 1, 1))) for i in range(num_samples)]
    p0 = (2 * points[0][0] - points[1][0], 2 * points[0][1] - points[1][1])
    pn = (2 * points[-1][0] - points[-2][0], 2 * points[-1][1] - points[-2][1])
    extended = [p0] + list(points) + [pn]
    sampled = []
    n_per_seg = max(1, num_samples // (len(points) - 1))
    for i in range(len(points) - 1):
        for j in range(n_per_seg):
            t = j / n_per_seg
            pt = catmull_rom_point(extended[i], extended[i + 1], extended[i + 2], extended[i + 3], t)
            sampled.append(pt)
    sampled.append(points[-1])
    return sampled


def interpolate_curve(points, t):
    """t from 0 to 1, 沿 Catmull-Rom 曲线弧长均匀插值"""
    if not points:
        return None
    if len(points) == 1:
        return {"x": points[0][0], "y": points[0][1]}
    sampled = sample_curve(points)
    if len(sampled) < 2:
        return {"x": points[0][0], "y": points[0][1]}
    lengths, total = [], 0
    for i in range(len(sampled) - 1):
        dx = sampled[i + 1][0] - sampled[i][0]
        dy = sampled[i + 1][1] - sampled[i][1]
        seg_len = math.sqrt(dx * dx + dy * dy)
        lengths.append(seg_len)
        total += seg_len
    if total < 1e-10:
        return {"x": sampled[0][0], "y": sampled[0][1]}
    target = t * total
    acc = 0
    for i, seg_len in enumerate(lengths):
        if acc + seg_len >= target:
            local_t = (target - acc) / seg_len if seg_len > 0 else 0
            x = lerp(sampled[i][0], sampled[i + 1][0], local_t)
            y = lerp(sampled[i][1], sampled[i + 1][1], local_t)
            return {"x": x, "y": y}
        acc += seg_len
    return {"x": sampled[-1][0], "y": sampled[-1][1]}


def interpolate_polyline(points, t):
    """t from 0 to 1, 沿折线均匀插值"""
    if not points:
        return None
    if len(points) == 1:
        return {"x": points[0][0], "y": points[0][1]}
    lengths = []
    total = 0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        seg_len = math.sqrt(dx * dx + dy * dy)
        lengths.append(seg_len)
        total += seg_len
    if total < 1e-10:
        return {"x": points[0][0], "y": points[0][1]}
    target = t * total
    acc = 0
    for i, seg_len in enumerate(lengths):
        if acc + seg_len >= target:
            local_t = (target - acc) / seg_len if seg_len > 0 else 0
            x = lerp(points[i][0], points[i + 1][0], local_t)
            y = lerp(points[i][1], points[i + 1][1], local_t)
            return {"x": x, "y": y}
        acc += seg_len
    return {"x": points[-1][0], "y": points[-1][1]}

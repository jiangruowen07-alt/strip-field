"""
BlendedFieldEngine - 多母线叠加、距离衰减、切向/法向加权混合
"""

import math

from config import T_COUNT, T_STEP
from curve import sample_curve
from utils import lerp


def _precompute_curve_arrays(points, num_samples=80):
    """预计算单条曲线的 (xs, ys, nxs, nys, txs, tys)"""
    if not points or len(points) < 2:
        return None
    sampled = sample_curve(points, num_samples=num_samples)
    if len(sampled) < 2:
        return None
    lengths, total = [], 0.0
    for i in range(len(sampled) - 1):
        dx = sampled[i + 1][0] - sampled[i][0]
        dy = sampled[i + 1][1] - sampled[i][1]
        seg = math.sqrt(dx * dx + dy * dy)
        lengths.append(seg)
        total += seg
    if total < 1e-10:
        return None
    xs, ys = [0.0] * T_COUNT, [0.0] * T_COUNT
    nxs, nys = [0.0] * T_COUNT, [0.0] * T_COUNT
    txs, tys = [0.0] * T_COUNT, [0.0] * T_COUNT
    acc, idx = 0.0, 0
    for i in range(T_COUNT):
        target = (i * T_STEP) * total
        while idx < len(lengths) and acc + lengths[idx] < target:
            acc += lengths[idx]
            idx += 1
        if idx >= len(lengths):
            xs[i], ys[i] = sampled[-1][0], sampled[-1][1]
        else:
            local_t = (target - acc) / lengths[idx] if lengths[idx] > 0 else 0
            xs[i] = lerp(sampled[idx][0], sampled[idx + 1][0], local_t)
            ys[i] = lerp(sampled[idx][1], sampled[idx + 1][1], local_t)
        i0, i1 = max(0, idx - 1), min(len(sampled) - 1, idx + 1)
        dx = sampled[i1][0] - sampled[i0][0]
        dy = sampled[i1][1] - sampled[i0][1]
        L = math.sqrt(dx * dx + dy * dy) or 1e-10
        txs[i] = dx / L
        tys[i] = dy / L
        nxs[i] = -tys[i]
        nys[i] = txs[i]
    return (xs, ys, nxs, nys, txs, tys)


def _point_to_curve_distance(px, py, xs, ys):
    """点到曲线的最短距离（近似：到采样点的最小距离）"""
    d_min = 1e30
    for i in range(T_COUNT):
        dx = px - xs[i]
        dy = py - ys[i]
        d = math.sqrt(dx * dx + dy * dy)
        if d < d_min:
            d_min = d
    return d_min


class BlendedFieldEngine:
    """
    多母线叠加场引擎。
    - 多母线叠加：多条母线的向量场加权求和
    - 距离衰减：按到母线的距离衰减权重
    - tangent / normal 加权混合：可调节切向与法向的混合比例
    """

    def __init__(self, tangent_weight=0.0, normal_weight=1.0, distance_decay=0.0, decay_radius=200.0):
        """
        Args:
            tangent_weight: 切向分量权重 (0~1)
            normal_weight: 法向分量权重 (0~1)，通常 tangent + normal 归一化
            distance_decay: 距离衰减系数，0=无衰减，越大衰减越快
            decay_radius: 衰减特征半径
        """
        self.tangent_weight = tangent_weight
        self.normal_weight = normal_weight
        self.distance_decay = distance_decay
        self.decay_radius = decay_radius

    def _distance_weight(self, d):
        """距离衰减权重：exp(-distance_decay * d / decay_radius)"""
        if self.distance_decay <= 0:
            return 1.0
        return math.exp(-self.distance_decay * d / max(self.decay_radius, 1e-6))

    def _blend_vector(self, tx, ty, nx, ny):
        """切向/法向加权混合，返回单位向量"""
        tw, nw = self.tangent_weight, self.normal_weight
        vx = tx * tw + nx * nw
        vy = ty * tw + ny * nw
        L = math.sqrt(vx * vx + vy * vy) or 1e-10
        return vx / L, vy / L

    def generate_lines(self, curves_data, state, line_spacing=40, pos_count=10, neg_count=10):
        """
        从多条母线生成叠加场线。
        curves_data: list of {"points": [(x,y),...], "weight": 1.0}
        """
        # 预计算每条曲线的数组
        arrays = []
        for c in curves_data:
            pts = c.get("points", c) if isinstance(c, dict) else c
            arr = _precompute_curve_arrays(pts)
            if arr:
                arrays.append((arr, c.get("weight", 1.0)))

        if not arrays:
            return []

        lines = []
        for side in range(2):
            count = pos_count if side == 1 else neg_count
            start_i = 1 if side == 0 else 0
            for i in range(start_i, count + 1):
                actual_index = -i if side == 0 else i
                offset_dist = actual_index * line_spacing
                line_points = []
                for ti in range(T_COUNT):
                    t = ti * T_STEP
                    px_sum, py_sum = 0.0, 0.0
                    w_sum = 0.0
                    for (xs, ys, nxs, nys, txs, tys), curve_weight in arrays:
                        base_x = xs[ti]
                        base_y = ys[ti]
                        nx, ny = nxs[ti], nys[ti]
                        tx, ty = txs[ti], tys[ti]
                        vx, vy = self._blend_vector(tx, ty, nx, ny)
                        # 偏移点
                        px = base_x + vx * offset_dist
                        py = base_y + vy * offset_dist
                        # 距离衰减
                        d = _point_to_curve_distance(px, py, xs, ys)
                        w = self._distance_weight(d) * curve_weight
                        px_sum += px * w
                        py_sum += py * w
                        w_sum += w
                    if w_sum > 1e-10:
                        px = px_sum / w_sum
                        py = py_sum / w_sum
                    else:
                        # fallback: 用第一条曲线
                        xs, ys = arrays[0][0][0], arrays[0][0][1]
                        nxs, nys = arrays[0][0][2], arrays[0][0][3]
                        txs, tys = arrays[0][0][4], arrays[0][0][5]
                        vx, vy = self._blend_vector(txs[ti], tys[ti], nxs[ti], nys[ti])
                        px = xs[ti] + vx * offset_dist
                        py = ys[ti] + vy * offset_dist
                    line_points.append({"x": px, "y": py, "t": t, "offset": offset_dist})
                lines.append(line_points)
        return lines

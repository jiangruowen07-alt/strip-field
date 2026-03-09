"""
向量场生成逻辑：预计算、扩张线生成
保留旧逻辑，通过 OffsetFieldEngine 实现；并导出新引擎。
"""

import math

from config import T_COUNT, T_STEP
from utils import lerp
from curve import sample_curve

# 新引擎（可选使用）
from engines.offset_field_engine import OffsetFieldEngine
from engines.blended_field_engine import BlendedFieldEngine
from engines.scalar_field_engine import ScalarFieldEngine
from engines.streamline_integrator import StreamlineIntegrator

__all__ = [
    "precompute_parametric_arrays",
    "precompute_custom_curve_arrays",
    "generate_lines_from_arrays",
    "OffsetFieldEngine",
    "BlendedFieldEngine",
    "ScalarFieldEngine",
    "StreamlineIntegrator",
]


def precompute_parametric_arrays(state):
    """预计算参数化母线在 t=0..1 的种子点与向量"""
    xs, ys = [0.0] * T_COUNT, [0.0] * T_COUNT
    nxs, nys = [0.0] * T_COUNT, [0.0] * T_COUNT
    txs, tys = [0.0] * T_COUNT, [0.0] * T_COUNT
    length_ratio = state["seedLength"]
    half_span = state["siteWidth"] * length_ratio * 0.5
    rad = state["seedRotation"] * math.pi / 180
    cx = state["siteWidth"] / 2 + state["seedXOffset"]
    cy = state["siteHeight"] / 2 + state["seedYOffset"]
    seed_type = state["seedType"]
    amp = state["seedSineAmp"]
    curv = state["seedArcCurv"]
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    for i in range(T_COUNT):
        t = i * T_STEP
        x = (t - 0.5) * 2 * half_span
        y = 0.0
        if seed_type == "sine":
            y = math.sin(t * math.pi * 2) * amp
        elif seed_type == "arc":
            y = ((t - 0.5) ** 2) * curv
        rx = x * cos_r - y * sin_r
        ry = x * sin_r + y * cos_r
        xs[i] = rx + cx
        ys[i] = ry + cy
    for i in range(T_COUNT):
        i0 = max(0, i - 1)
        i1 = min(T_COUNT - 1, i + 1)
        dx = xs[i1] - xs[i0]
        dy = ys[i1] - ys[i0]
        L = math.sqrt(dx * dx + dy * dy) or 1e-10
        txs[i] = dx / L
        tys[i] = dy / L
        nxs[i] = -tys[i]
        nys[i] = txs[i]
    return (xs, ys, nxs, nys, txs, tys)


def precompute_custom_curve_arrays(points):
    """预计算自定义母线在 t=0..1 的种子点与向量"""
    if not points or len(points) < 2:
        return None
    sampled = sample_curve(points, num_samples=80)
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


def generate_lines_from_arrays(arr, state, params=None):
    """
    从预计算数组生成扩张线。
    使用 OffsetFieldEngine，保留原有 7 种模式逻辑。
    params 可覆盖 state 中的参数（用于单条母线自定义参数，含 fieldType）
    """
    engine = OffsetFieldEngine.from_state(state, params)
    return engine.generate_lines(arr, state, params)

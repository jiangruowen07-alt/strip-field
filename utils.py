"""
通用工具函数
"""

import math


def lerp(a, b, t):
    """线性插值"""
    return a + (b - a) * t


def noise(x, y):
    """简易噪声函数 (Lattice Noise)"""
    return (math.sin(x * 0.01) * math.cos(y * 0.01) + math.sin(x * 0.02 + y * 0.015)) * 0.5


def safe_float(val, default):
    """安全转换为 float"""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default):
    """安全转换为 int"""
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default

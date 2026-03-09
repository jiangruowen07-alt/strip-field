"""
中英双语 UI 文案
"""

T = {
    "title": "Urban Field Gen / 城市线驱动向量场",
    "subtitle": "V.1.0 LINE-DRIVEN ENGINE / 线驱动引擎",
    "section_run_mode": "RUN MODE & SITE / 运行模式与场地",
    "section_field_logic": "FIELD LOGIC / 场逻辑",
    "section_seed_line": "SEED LINE / 母线",
    "section_multi_seed": "MULTI SEED LINES / 多条母线",
    "section_curve_params": "CURVE VECTOR PARAMS / 母线向量参数",
    "section_expansion": "EXPANSION PARAMETERS / 扩张参数",
    "section_noise": "NOISE & DISTORTION / 噪声与扰动",
    "section_street": "STREET & PARCEL (B/C) / 街道与地块",
    "run_mode": "Run Mode / 运行模式",
    "site_width": "Site Width / 场地宽度",
    "site_height": "Site Height / 场地高度",
    "engine": "Engine / 引擎",
    "field_type": "Field Type / 场类型",
    "seed_type": "Seed Line Type / 种子线类型",
    "seed_rotation": "Seed Rotation / 种子旋转",
    "seed_x_offset": "Seed X Offset / 种子 X 偏移",
    "seed_y_offset": "Seed Y Offset / 种子 Y 偏移",
    "seed_length": "Seed Length / 种子长度",
    "sine_amplitude": "Sine Amplitude / 正弦振幅",
    "arc_curvature": "Arc Curvature / 弧线曲率",
    "line_spacing": "Line Spacing / 线间距",
    "pos_count": "Pos. Count / 正向数量",
    "neg_count": "Neg. Count / 负向数量",
    "spacing_mode": "Spacing Mode / 间距模式",
    "spacing_scale": "Spacing Scale / 间距缩放",
    "noise_scale": "Noise Scale / 噪声尺度",
    "noise_strength": "Noise Strength / 噪声强度",
    "cross_spacing": "Cross Road Spacing / 横向道路间距",
    "parcel_min": "Parcel Min / 地块最小",
    "parcel_max": "Parcel Max / 地块最大",
    "parcel_depth": "Parcel Depth Offset / 地块深度偏移",
    "export_rhino": "Export for Rhino / 导出到 Rhino",
    "export_py": "Export .py (RhinoScript) / 导出 .py",
    "export_dxf": "Export DXF / 导出 DXF",
    "footer": "Non-Radial Field Generator\nUrban Morphology Study Tool / 非径向场生成器\n城市形态学研究工具",
    "status_default": "COORD_SYSTEM: CARTESIAN / 笛卡尔坐标系\nEXPANSION_VECTOR: LINE_LOCAL_NORMAL / 扩张向量: 线局部法向\nSTATUS: REALTIME_CALCULATION / 状态: 实时计算",
}

# 下拉选项（保持解析兼容的 key 词）
RUN_MODE_OPTS = [
    "A - Flow Lines / A - 流线",
    "B - Street Network / B - 街道网络",
    "C - Parcel Blocks / C - 地块",
]
ENGINE_OPTS = [
    "A. Offset (母线偏移) / A. Offset",
    "B. Blended (多母线叠加) / B. Blended",
    "C. Scalar+Streamline (标量场流线) / C. Scalar+Streamline",
]
FIELD_TYPE_OPTS = [
    "1. Parallel Offset / 平行偏移",
    "2. Curve Tangent / 曲线切向",
    "3. Curve Normal / 曲线法向",
    "4. Distance Contour / 距离等高线",
    "5. Strip Growth / 条带生长",
    "6. Hybrid Tangent-Normal / 混合切向-法向",
    "7. Noise-Modified Line Field / 噪声修正线场",
]
SEED_TYPE_OPTS = [
    "Straight Line / 直线",
    "Sine Wave / 正弦波",
    "Arc / Curve / 弧线",
    "Custom (Hand-drawn) / 自定义(手绘)",
]
SPACING_MODE_OPTS = [
    "Linear / 线性",
    "Exponential Expansion / 指数扩张",
    "Fibonacci Series / 斐波那契数列",
]
CURVE_SPACING_MODES = {"Linear / 线性": "linear", "Exponential / 指数": "exponential", "Fibonacci / 斐波那契": "fibonacci"}
INTEGRATE_METHOD_OPTS = ["Euler / 欧拉", "RK4 / 四阶龙格库塔"]

# 按钮与提示
BTN_ADD_CURVE = "+ Add Curve / + 添加母线"
BTN_DRAW = "Draw / Edit / 绘制 / 编辑"
BTN_DONE_DRAWING = "Done Drawing / 完成绘制"
BTN_CLEAR = "Clear All / 清空全部"
BTN_RESET = "Reset / 重置"
BTN_GENERATE = "Generate / 生成"
BTN_PARAMS = "Params / 参数"
BTN_EDIT = "Edit / 编辑"
BTN_DEL = "Del / 删除"

# 引擎专属
BLEND_PARAMS_TITLE = "Blended Params / 多母线叠加参数"
BLEND_TANGENT = "Tangent Weight / 切向权重"
BLEND_NORMAL = "Normal Weight / 法向权重"
BLEND_DECAY = "Distance Decay / 距离衰减"
BLEND_RADIUS = "Decay Radius / 衰减半径"
BLEND_HINT = "Select Custom and add multiple curves / 需选择 Custom 并添加多条母线"

SCALAR_PARAMS_TITLE = "Scalar Streamline Params / 标量场流线参数"
SCALAR_METHOD = "Integration Method / 积分方法"
SCALAR_STEP = "Step Size / 步长"
SCALAR_COUNT = "Streamline Count / 流线数量"
SCALAR_CENTER_X = "Land Price Center X / 地价中心 X"
SCALAR_CENTER_Y = "Land Price Center Y / 地价中心 Y"
SCALAR_SIGMA = "Land Price Spread σ / 地价扩散 σ"

OFFSET_HINT = "Use Field Type below for offset mode / 使用下方 Field Type 选择偏移模式"

# 曲线参数
MULTI_SEED_HINT = "Select Custom to add multiple curves, each can be hand-drawn / 选择 Custom 后可添加多条母线，每条均可手绘"
CURVE_PARAMS_HINT = "Select a curve in list to adjust its vector params / 选择母线后调整其向量位置、疏密等"
CURVE_SELECT_HINT = "(Click Params in list to select curve) / (点击列表中的 Params 选择母线)"
def curve_n_params(n):
    return f"Curve {n} Vector Params / 母线 {n} 向量参数"

def curve_n_pts(i, n):
    return f"Curve {i} ({n} pts) / 母线 {i} ({n} 点)"
LINE_SPACING_SHORT = "Line Spacing / 线间距"
POS_NEG = "Pos. / Neg. / 正向 / 负向"
OFFSET_XY = "Offset X/Y / 偏移 X/Y"
SPACING_MODE_SHORT = "Spacing Mode / 间距模式"
SPACING_SCALE_SHORT = "Spacing Scale / 间距缩放"
CROSS_SPACING_SHORT = "Road Density / 道路疏密"

# 勾选
NOISE_ENABLED = "Enable Noise Distortion / 启用噪声扰动"
ROADS_PERP = "Roads ⊥ Vector Lines / 路网⊥向量线"

# 曲线列表
NO_CURVES_YET = "(No curves yet. Click + Add Curve) / (暂无母线，点击 + 添加母线)"
DRAW_MODE_STATUS = "DRAW MODE: Curve {} - Click to add points, drag to move / 绘制模式: 母线 {} - 点击添加点，拖动移动"

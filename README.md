# Strip Field / Urban Field Generator

**城市线驱动向量场生成器** — 基于 Seed Curve 的非中心式扩张，用于城市形态学研究与参数化设计。

## 简介

本工具通过一条种子曲线（Seed Curve）生成可配置的向量场，支持多种扩张模式与场类型，可输出流线、街道网络和地块划分，适用于城市设计、形态学研究和参数化生成。

## 功能特性

- **三种运行模式**
  - **A - Flow Lines**：流线模式，展示向量场方向
  - **B - Street Network**：街道网络模式，生成纵向主街与横向连接
  - **C - Parcel Blocks**：地块模式，在街道网络基础上划分地块

- **七种场类型**
  1. Parallel Offset（平行偏移）
  2. Curve Tangent（曲线切向）
  3. Curve Normal（曲线法向）
  4. Distance Contour（距离等高线）
  5. Strip Growth（条带生长）
  6. Hybrid Tangent-Normal（混合切向-法向）
  7. Noise-Modified Line Field（噪声修正线场）

- **种子线类型**：直线、正弦波、弧线/曲线
- **扩张参数**：线间距、正负向数量、间距模式（线性 / 指数 / 斐波那契）、间距缩放
- **噪声与扰动**：可选的噪声扭曲，支持调节噪声尺度与强度
- **街道与地块参数**：横向道路间距、地块最小/最大面宽、最小面积、最大进深
- **地块划分模式**：临街面切分、按块切分、转角地块单独、不规则扰动（可单独开关）
- **道路等级**：primary / secondary / local，主骨架更明显
- **自适应横街**：根据曲率、吸引子距离、地价价值决定横街密度，不再固定 t 采样

## 环境要求

- Python 3.x
- 标准库：`tkinter`（通常随 Python 安装）

## 安装与运行

```bash
# 克隆或进入项目目录
cd strip-field

# 直接运行（无需额外依赖）
python main.py
```

## 使用说明

1. 启动程序后，左侧为控制面板，右侧为预览画布。
2. 调整参数后，结果会实时更新。
3. 点击 **Generate** 重新生成，点击 **Reset** 恢复默认参数。
4. 可调整场地尺寸（Site Width / Height）、种子旋转、线间距等参数。
5. 在 Mode B 或 C 下可进一步设置街道与地块相关参数。
6. **导出到 Rhino**：点击 **Export .py (RhinoScript)** 保存 Python 脚本，在 Rhino 中打开 **EditPythonScript**，运行该脚本即可在视图中生成曲线；或点击 **Export DXF** 导出 DXF 文件（需 `pip install ezdxf`），在 Rhino 中直接导入。导出时以场地矩形（Site Width × Site Height）为边界，自动裁剪掉超出边界的线，仅保留内部部分。

## 项目结构

```
strip-field/
├── main.py              # 程序入口
├── app.py               # 主应用类 UrbanFieldGenerator（UI + 逻辑编排）
├── parcel_subdivision.py # 地块划分（frontage-based、block-by-block、转角、扰动）
├── config.py            # 配置常量（T_STEP, T_COUNT）
├── utils.py             # 工具函数（lerp, noise, safe_float, safe_int）
├── geom.py              # 几何裁剪（线段/折线/多边形裁剪到矩形）
├── curve.py             # 曲线插值（Catmull-Rom 样条、弧长采样）
├── field_generator.py   # 向量场生成逻辑（预计算、扩张线生成）
├── street_network.py    # 街道网络（道路等级、自适应横街）
├── engines/             # 向量场引擎模块
│   ├── offset_field_engine.py   # A. OffsetFieldEngine（原有 7 种模式）
│   ├── blended_field_engine.py  # B. BlendedFieldEngine（多母线叠加、距离衰减、切向/法向混合）
│   ├── scalar_field_engine.py   # C. ScalarFieldEngine（标量场→梯度场→垂直流线）
│   └── streamline_integrator.py # D. StreamlineIntegrator（Euler/RK4 流线积分）
├── exporter.py          # 导出逻辑（RhinoScript、DXF）
├── urban_field_gen.py   # 旧版单文件（保留作参考）
├── requirements.txt     # 可选依赖（DXF 导出需 ezdxf）
└── README.md
```

## 引擎架构

- **A. OffsetFieldEngine**：保留原有逻辑，支持 parallel、tangent_drift、normal_band、contour_bulge、strip_growth、hybrid、noise_modified 七种模式。
- **B. BlendedFieldEngine**：多母线叠加、距离衰减、tangent/normal 加权混合，适合多条曲线共同影响场。
- **C. ScalarFieldEngine**：从标量场（如地价）生成梯度场，再生成垂直于梯度的流线，适合等高线逻辑。
- **D. StreamlineIntegrator**：支持 Euler / RK4 积分，从 seed points 积分出真正流线。

## 技术说明

- 采用笛卡尔坐标系，扩张向量基于曲线局部法向。
- 使用 Lattice Noise 实现简易噪声扰动。
- 界面为 Tkinter 深色主题，适合长时间使用。

## 版本

V.1.0 — Line-Driven Engine

## 许可证

仅供学习与研究使用。

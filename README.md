# ◈ RS Index Calculator

> 面向遥感初学者的桌面端遥感指数批量计算工具
> 无需 GEE 账号 · 无需编程基础 · 开箱即用

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00D4A1?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey?style=flat-square)
![AI Assisted](https://img.shields.io/badge/AI%20Assisted-Claude%20by%20Anthropic-blueviolet?style=flat-square)

---

## 项目简介

下载完 Landsat 或哨兵数据之后，总要在 ENVI 里一遍遍手动选波段、写公式；用 GEE 又需要学 JavaScript 和处理网络问题。

`RS Index Calculator` 是一个专门解决这个痛点的桌面工具：把传感器波段配置、常用指数公式全部内置，直接用 MTL 文件或 .SAFE 文件夹导入原始数据，勾选指数，一键计算，结果自动预览。

```
对标 ENVI 的波段运算功能，但更简单，并且免费开源。
```

> 🤖 本项目由作者独立设计（需求规划、传感器配置、指数选型），代码实现部分借助 AI 工具（Claude by Anthropic）辅助生成。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| **智能原始数据导入** | Landsat 选 MTL 文件自动识别全部波段；Sentinel-2 选 .SAFE 文件夹自动匹配 jp2 |
| **30+ 内置指数** | 覆盖植被、水体、城市、土壤、积雪、火灾、干旱、热红外 8 大类别 |
| **自定义指数** | 输入 NumPy 公式 → 测试验证 → 永久保存，像 ENVI 波段运算但更方便 |
| **多格式读写** | 读取 GeoTIFF / ENVI(.img/.dat) / Sentinel-2 jp2；输出支持 GeoTIFF 或 ENVI 格式 |
| **波段信息弹窗** | 导入文件时自动读取波段数、数据类型、采样统计，方便核对 |
| **结果预览** | 计算完成自动渲染伪彩色图，显示 min/max/mean 统计值 |
| **数据来源导航** | 内置 11 个平台链接，含国内地理空间数据云、高分数据，国际 USGS/NASA/ESA 等 |
| **批量处理** | 支持多文件 × 多指数，一次运行全部输出 |
| **保留地理信息** | 输出文件完整保留原始 CRS、Transform、投影 |

---

## 快速上手

### 安装依赖

推荐使用 conda，可以避免 Windows 上 GDAL 依赖问题：

```bash
conda create -n rs_calc python=3.9
conda activate rs_calc
conda install -c conda-forge rasterio numpy matplotlib
```

或者使用 pip：

```bash
pip install rasterio numpy matplotlib
```

> ⚠️ Windows 用户**强烈建议**使用 conda-forge 安装 rasterio，直接 pip 安装在 Windows 上容易缺失 GDAL 相关 DLL。

### 运行

将以下三个文件放在同一文件夹：

```
rs_calculator.py
smart_importer.py
data_sources.py
```

然后运行：

```bash
python rs_calculator.py
```

---

## 使用流程

### 方式一：智能导入（推荐，适合原始数据）

适合刚从 USGS、地理空间数据云下载的原始数据包。

**Landsat 数据：**

1. 解压下载的 Landsat 压缩包，得到一个含有 `*_MTL.txt` 和多个 `*_B*.TIF` 的文件夹
2. 点击主界面的 **⚡ 智能导入**
3. 选择 **"选择 Landsat MTL 文件"**，找到文件夹里的 `*_MTL.txt` 或 `*_MTL.json`
4. 弹窗会显示自动识别的传感器、产品级别、所有波段的匹配情况
5. 点击 **"导入并立即计算"** 或 **"仅导入"** 回到主界面手动勾选指数

> L2 Collection 2 数据的缩放系数（×2.75e-5，偏移 −0.2）会自动设置，无需手动填写。

**Sentinel-2 数据：**

1. 解压下载的 `.SAFE.zip`，得到 `S2A_MSIL2A_******.SAFE` 文件夹
2. 点击 **⚡ 智能导入** → **"选择 Sentinel-2 .SAFE 文件夹"**
3. 选择分辨率（默认 10m，含 B02/B03/B04/B08；20m 可额外得到红边和 SWIR 波段）
4. 确认波段匹配后导入

> 选 10m 时 B05/B06/B07/B11/B12 等波段会自动从 20m/60m 目录补充，无需担心缺失。

---

### 方式二：手动导入（适合已处理的数据）

适合经过 ENVI 大气校正、裁剪等处理后保存的 `.tif`、`.img`、`.dat` 文件。

1. 在 **① 数据 & 指数** 标签页，选择传感器类型
2. 点击 **+ 添加** 选择文件（支持 `.tif/.tiff/.img/.dat/.hdr`）
3. 每个文件导入时会弹出**波段信息窗口**，显示波段数、数据类型和采样统计，确认后添加
4. 如果波段顺序与默认不同，前往 **③ 波段映射** 标签页修改对应编号
5. 设置好 NoData 值和缩放系数（已做过地表反射率转换的数据缩放填 1.0）

---

### 勾选指数并计算

1. 在指数列表里按类别筛选，或直接全选
2. 鼠标悬停在任意指数上，底部会显示完整公式、值域、适用场景
3. 灰色的指数表示当前传感器缺少所需波段（如 Landsat 5 无 RedEdge，NDRE 置灰）
4. 选好输出路径和输出格式（GeoTIFF 或 ENVI），点击 **▶ 开始计算**
5. 运行日志实时显示读取和计算进度
6. 完成后自动跳转到 **④ 结果预览**

---

### 自定义指数

在 **② 自定义指数** 标签页，使用逻辑波段名写 Python/NumPy 公式：

```python
# 可用的逻辑波段名
NIR, Red, Green, Blue, SWIR1, SWIR2, RedEdge1, RedEdge2, RedEdge3, Coastal, TIR1, TIR2

# 支持全部 NumPy 函数
np.sqrt, np.log, np.exp, np.abs ...

# 示例
(NIR - Red) / (NIR + Red)                       # 等同于 NDVI
4*(Green-SWIR1) - (0.25*NIR + 2.75*SWIR2)      # 等同于 AWEI_nsh
np.sqrt(NIR) - Red                               # 自定义探索
```

点击 **▶ 测试公式** 验证语法，通过后 **+ 添加到列表**，自动保存到本地 `custom_indices.json`。

---

## 内置指数列表（30+）

### 🌿 植被（13 个）

| 指数 | 全称 | 所需波段 |
|------|------|----------|
| NDVI | Normalized Difference Vegetation Index | NIR, Red |
| EVI | Enhanced Vegetation Index | NIR, Red, Blue |
| EVI2 | Two-band EVI（无需蓝波段）| NIR, Red |
| SAVI | Soil-Adjusted Vegetation Index | NIR, Red |
| MSAVI2 | Modified SAVI 2 | NIR, Red |
| OSAVI | Optimized SAVI | NIR, Red |
| ARVI | Atmospherically Resistant VI | NIR, Red, Blue |
| GNDVI | Green NDVI | NIR, Green |
| NDRE | Normalized Difference Red Edge | NIR, RedEdge1 |
| VARI | Visible Atmospherically Resistant Index | Green, Red, Blue |
| RVI | Ratio Vegetation Index | NIR, Red |
| DVI | Difference Vegetation Index | NIR, Red |
| WDRVI | Wide Dynamic Range VI | NIR, Red |

### 💧 水体（6 个）

| 指数 | 全称 | 特点 |
|------|------|------|
| NDWI | Normalized Difference Water Index | McFeeters 1996 |
| MNDWI | Modified NDWI | 城市区域推荐 |
| AWEI_nsh | Automated Water Extraction Index (no shadow) | 复杂环境高精度 |
| AWEI_sh | AWEI with Shadow Elimination | 消除阴影干扰 |
| WRI | Water Ratio Index | 浅水和浑浊水体 |
| NDMI | Normalized Difference Moisture Index | 植被水分监测 |

### 🏙️ 城市（3 个）· 🟤 土壤（3 个）· ❄️🔥☀️🌡️ 其他（7 个）

| 指数 | 类别 | 说明 |
|------|------|------|
| NDBI / UI / IBI | 城市 | 建筑区识别与城市扩张 |
| BSI / RI / SATVI | 土壤 | 裸土识别与土壤属性 |
| NDSI | 积雪 | >0.4 为积雪 |
| NBR / NBR2 / BAI | 火灾 | 火灾烈度与火烧迹地 |
| NDDI / NMDI | 干旱 | 植被水分综合旱情监测 |
| NDLST | 热红外 | 热波段差值分析 |

---

## 支持的数据格式

| 类型 | 格式 | 备注 |
|------|------|------|
| 输入 | GeoTIFF `.tif/.tiff` | Landsat 单波段 TIF |
| 输入 | ENVI `.img/.dat/.bil` | 需配套 `.hdr` 文件 |
| 输入 | Sentinel-2 `.jp2` | 通过智能导入处理 |
| 输出 | GeoTIFF `.tif` | 默认格式，通用性强 |
| 输出 | ENVI `.img/.dat` | 可直接在 ENVI 中打开 |

---

## 内置数据来源导航

在 **⑥ 数据来源** 标签页，收录以下平台：

**中国** — 地理空间数据云 / 高分数据服务（CRESDA）/ 天地图 / 自然资源卫星云平台

**国际** — USGS EarthExplorer / NASA Earthdata / ESA Copernicus Data Space / ASF / OpenTopography / NOAA / Copernicus Global Land

---

## 文件结构

```
rs-index-calculator/
├── rs_calculator.py      # 主程序（GUI + 计算逻辑）
├── smart_importer.py     # 智能导入模块（Landsat MTL / Sentinel-2 SAFE）
├── data_sources.py       # 数据来源导航模块
├── requirements.txt      # 依赖列表
└── README.md
```

运行后自动生成（请勿删除）：

```
custom_indices.json       # 用户保存的自定义指数
```

---

## 打包为 EXE（Windows）

```bash
pip install pyinstaller

# 注意：必须用 -D 文件夹模式，-F 单文件模式会导致 rasterio 找不到 GDAL
pyinstaller -D -w --collect-all rasterio --collect-all pyproj rs_calculator.py
```

打包后将 `smart_importer.py` 和 `data_sources.py` 放入 `dist/rs_calculator/` 文件夹，将整个文件夹分发给用户。

---

## 常见问题

**Q: 报错 `No module named 'rasterio'`**
使用 `conda install -c conda-forge rasterio` 安装，不建议 pip 安装（Windows 上 DLL 容易缺失）。

**Q: Landsat 导入后某些波段缺失**
L2SP 产品才包含热红外（ST_B10），L2SR 只有地表反射率波段。请确认下载的是 L2SP 级别。

**Q: Sentinel-2 的 NDRE 置灰**
NDRE 需要 B05（RedEdge1），该波段仅在 20m 分辨率存在。智能导入时选择分辨率 20m 即可。

**Q: ENVI 处理后的数据缩放系数填多少**
如果 ENVI 输出的已是地表反射率（0~1 范围），填 `1.0`；如果是 DN 值，需根据传感器填对应系数。

---

## 后续计划

- [ ] MODIS HDF 智能导入支持
- [ ] dNBR 变化检测（火前-火后差值）
- [ ] 批量时序处理（同区域多景影像）
- [ ] 统计报告导出（面积统计、分级结果）
## ⬇ 下载

Windows 用户可直接下载打包好的版本，无需安装 Python：（在releases中）

> 解压后运行 `RS_Index_Calculator.exe` 即可，首次启动可能需要等待几秒。
---

## 依赖

| 库 | 版本 | 是否必须 |
|----|------|----------|
| rasterio | ≥ 1.3 | ✅ |
| numpy | ≥ 1.21 | ✅ |
| matplotlib | ≥ 3.5 | 可选（结果预览用）|
| tkinter | 标准库 | ✅ |

---

## 致谢

- [Rasterio](https://github.com/rasterio/rasterio)
- [Awesome Spectral Indices](https://github.com/awesome-spectral-indices/awesome-spectral-indices)
- [USGS Landsat](https://www.usgs.gov/landsat-missions)
- [ESA Sentinel](https://sentinel.esa.int/)

---

## License

MIT License © 2025

欢迎 fork、提 Issue 和 PR。如果对你有帮助，欢迎点 ⭐ Star！

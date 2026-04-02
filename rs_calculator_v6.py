"""
RS Index Calculator v2.0
遥感指数批量计算工具
支持 Landsat 5/7/8/9, Sentinel-2, MODIS
功能：30+ 内置指数 | 自定义公式 | 结果预览
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import json
import math
from pathlib import Path

try:
    from smart_importer_v2 import SmartImportDialog
    SMART_IMPORT_AVAILABLE = True
except ImportError:
    SMART_IMPORT_AVAILABLE = False

try:
    from data_sources import build_data_source_tab
    DATA_SOURCES_AVAILABLE = True
except ImportError:
    DATA_SOURCES_AVAILABLE = False

try:
    import numpy as np
    import rasterio
    from rasterio.enums import ColorInterp
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ══════════════════════════════════════════════════════
#  传感器波段配置
# ══════════════════════════════════════════════════════
SENSOR_BANDS = {
    "Landsat 5 (TM)": {
        "Blue":  {"band": 1,  "wavelength": "0.45–0.52 µm"},
        "Green": {"band": 2,  "wavelength": "0.52–0.60 µm"},
        "Red":   {"band": 3,  "wavelength": "0.63–0.69 µm"},
        "NIR":   {"band": 4,  "wavelength": "0.76–0.90 µm"},
        "SWIR1": {"band": 5,  "wavelength": "1.55–1.75 µm"},
        "TIR":   {"band": 6,  "wavelength": "10.40–12.50 µm"},
        "SWIR2": {"band": 7,  "wavelength": "2.08–2.35 µm"},
    },
    "Landsat 7 (ETM+)": {
        "Blue":  {"band": 1,  "wavelength": "0.45–0.52 µm"},
        "Green": {"band": 2,  "wavelength": "0.52–0.60 µm"},
        "Red":   {"band": 3,  "wavelength": "0.63–0.69 µm"},
        "NIR":   {"band": 4,  "wavelength": "0.77–0.90 µm"},
        "SWIR1": {"band": 5,  "wavelength": "1.55–1.75 µm"},
        "TIR":   {"band": 6,  "wavelength": "10.40–12.50 µm"},
        "SWIR2": {"band": 7,  "wavelength": "2.09–2.35 µm"},
        "PAN":   {"band": 8,  "wavelength": "0.52–0.90 µm"},
    },
    "Landsat 8/9 (OLI)": {
        "Coastal": {"band": 1,  "wavelength": "0.43–0.45 µm"},
        "Blue":    {"band": 2,  "wavelength": "0.45–0.51 µm"},
        "Green":   {"band": 3,  "wavelength": "0.53–0.59 µm"},
        "Red":     {"band": 4,  "wavelength": "0.64–0.67 µm"},
        "NIR":     {"band": 5,  "wavelength": "0.85–0.88 µm"},
        "SWIR1":   {"band": 6,  "wavelength": "1.57–1.65 µm"},
        "SWIR2":   {"band": 7,  "wavelength": "2.11–2.29 µm"},
        "TIR1":    {"band": 10, "wavelength": "10.60–11.19 µm"},
        "TIR2":    {"band": 11, "wavelength": "11.50–12.51 µm"},
    },
    "Sentinel-2 (MSI)": {
        "Coastal":   {"band": 1,  "wavelength": "0.443 µm"},
        "Blue":      {"band": 2,  "wavelength": "0.490 µm"},
        "Green":     {"band": 3,  "wavelength": "0.560 µm"},
        "Red":       {"band": 4,  "wavelength": "0.665 µm"},
        "RedEdge1":  {"band": 5,  "wavelength": "0.705 µm"},
        "RedEdge2":  {"band": 6,  "wavelength": "0.740 µm"},
        "RedEdge3":  {"band": 7,  "wavelength": "0.783 µm"},
        "NIR":       {"band": 8,  "wavelength": "0.842 µm"},
        "NIR_N":     {"band": 9,  "wavelength": "0.865 µm"},
        "SWIR1":     {"band": 11, "wavelength": "1.610 µm"},
        "SWIR2":     {"band": 12, "wavelength": "2.190 µm"},
    },
    "MODIS (Terra/Aqua)": {
        "Red":   {"band": 1, "wavelength": "0.620–0.670 µm"},
        "NIR":   {"band": 2, "wavelength": "0.841–0.876 µm"},
        "Blue":  {"band": 3, "wavelength": "0.459–0.479 µm"},
        "Green": {"band": 4, "wavelength": "0.545–0.565 µm"},
        "SWIR1": {"band": 5, "wavelength": "1.230–1.250 µm"},
        "SWIR2": {"band": 6, "wavelength": "1.628–1.652 µm"},
        "SWIR3": {"band": 7, "wavelength": "2.105–2.155 µm"},
    },
}

# ══════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════
def safe_div(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(b != 0, a / b, np.nan)

def safe_sqrt(a):
    return np.sqrt(np.abs(a)) * np.sign(a)

# ══════════════════════════════════════════════════════
#  内置指数定义（30+个）
# ══════════════════════════════════════════════════════
INDEX_DEFINITIONS = {

    # ── 植被 Vegetation ──────────────────────────────
    "NDVI": {
        "full_name": "Normalized Difference Vegetation Index",
        "formula_display": "(NIR - Red) / (NIR + Red)",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "最常用植被指数。>0.2 为植被，越高越茂密；<0 为水体或云。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["NIR"] - b["Red"], b["NIR"] + b["Red"]),
    },
    "EVI": {
        "full_name": "Enhanced Vegetation Index",
        "formula_display": "2.5*(NIR-Red)/(NIR+6*Red-7.5*Blue+1)",
        "bands": ["NIR", "Red", "Blue"],
        "range": "[-1, 1]",
        "description": "增强植被指数，减少大气和土壤背景影响，高植被密度区优于NDVI。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: 2.5 * safe_div(b["NIR"] - b["Red"], b["NIR"] + 6*b["Red"] - 7.5*b["Blue"] + 1),
    },
    "EVI2": {
        "full_name": "Two-band Enhanced Vegetation Index",
        "formula_display": "2.4*(NIR-Red)/(NIR+Red+1)",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "无需蓝波段的EVI简化版，适用于无Blue波段传感器（如AVHRR）。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: 2.4 * safe_div(b["NIR"] - b["Red"], b["NIR"] + b["Red"] + 1),
    },
    "SAVI": {
        "full_name": "Soil-Adjusted Vegetation Index",
        "formula_display": "1.5*(NIR-Red)/(NIR+Red+0.5)",
        "bands": ["NIR", "Red"],
        "range": "[-1.5, 1.5]",
        "description": "土壤调整植被指数（L=0.5），稀疏植被区优于NDVI，降低土壤亮度影响。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: 1.5 * safe_div(b["NIR"] - b["Red"], b["NIR"] + b["Red"] + 0.5),
    },
    "MSAVI2": {
        "full_name": "Modified Soil-Adjusted Vegetation Index 2",
        "formula_display": "(2*NIR+1-sqrt((2*NIR+1)²-8*(NIR-Red)))/2",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "改进土壤调整植被指数，无需指定L值，适用于高裸土覆盖区和早期作物监测。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(
            2*b["NIR"] + 1 - safe_sqrt((2*b["NIR"]+1)**2 - 8*(b["NIR"]-b["Red"])), 2
        ),
    },
    "OSAVI": {
        "full_name": "Optimized Soil-Adjusted Vegetation Index",
        "formula_display": "(NIR-Red)/(NIR+Red+0.16)",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "优化土壤调整植被指数，农业监测优于SAVI，对低密度植被更敏感。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["NIR"] - b["Red"], b["NIR"] + b["Red"] + 0.16),
    },
    "ARVI": {
        "full_name": "Atmospherically Resistant Vegetation Index",
        "formula_display": "(NIR-(2*Red-Blue))/(NIR+(2*Red-Blue))",
        "bands": ["NIR", "Red", "Blue"],
        "range": "[-1, 1]",
        "description": "大气阻抗植被指数，对大气气溶胶不敏感，适用于大气污染严重地区。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(
            b["NIR"] - (2*b["Red"] - b["Blue"]),
            b["NIR"] + (2*b["Red"] - b["Blue"])
        ),
    },
    "GNDVI": {
        "full_name": "Green Normalized Difference Vegetation Index",
        "formula_display": "(NIR-Green)/(NIR+Green)",
        "bands": ["NIR", "Green"],
        "range": "[-1, 1]",
        "description": "绿波段NDVI，对叶绿素含量更敏感，适用于成熟期作物氮含量监测。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["NIR"] - b["Green"], b["NIR"] + b["Green"]),
    },
    "NDRE": {
        "full_name": "Normalized Difference Red Edge Index",
        "formula_display": "(NIR-RedEdge1)/(NIR+RedEdge1)",
        "bands": ["NIR", "RedEdge1"],
        "range": "[-1, 1]",
        "description": "红边指数，对叶绿素和氮含量极敏感，可提前检测植被胁迫（需Sentinel-2）。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["NIR"] - b["RedEdge1"], b["NIR"] + b["RedEdge1"]),
    },
    "VARI": {
        "full_name": "Visible Atmospherically Resistant Index",
        "formula_display": "(Green-Red)/(Green+Red-Blue)",
        "bands": ["Green", "Red", "Blue"],
        "range": "[-1, 1]",
        "description": "可见光大气阻抗指数，仅用可见光波段估算植被覆盖度，适用于RGB影像。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["Green"] - b["Red"], b["Green"] + b["Red"] - b["Blue"]),
    },
    "RVI": {
        "full_name": "Ratio Vegetation Index",
        "formula_display": "NIR/Red",
        "bands": ["NIR", "Red"],
        "range": "[0, ∞)",
        "description": "比值植被指数，是NDVI的前身，对高生物量区不饱和，但对噪声较敏感。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(b["NIR"], b["Red"]),
    },
    "DVI": {
        "full_name": "Difference Vegetation Index",
        "formula_display": "NIR - Red",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "差值植被指数，对土壤背景敏感，主要用于植被识别。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: b["NIR"] - b["Red"],
    },
    "WDRVI": {
        "full_name": "Wide Dynamic Range Vegetation Index",
        "formula_display": "(0.2*NIR-Red)/(0.2*NIR+Red)",
        "bands": ["NIR", "Red"],
        "range": "[-1, 1]",
        "description": "宽动态范围植被指数，高密度植被区比NDVI具有更大动态范围。",
        "category": "Vegetation",
        "colormap": "RdYlGn",
        "func": lambda b: safe_div(0.2*b["NIR"] - b["Red"], 0.2*b["NIR"] + b["Red"]),
    },

    # ── 水体 Water ───────────────────────────────────
    "NDWI": {
        "full_name": "Normalized Difference Water Index (McFeeters)",
        "formula_display": "(Green-NIR)/(Green+NIR)",
        "bands": ["Green", "NIR"],
        "range": "[-1, 1]",
        "description": "水体指数，>0 为水体（McFeeters 1996）。对水体识别有效但易混淆建筑。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: safe_div(b["Green"] - b["NIR"], b["Green"] + b["NIR"]),
    },
    "MNDWI": {
        "full_name": "Modified Normalized Difference Water Index",
        "formula_display": "(Green-SWIR1)/(Green+SWIR1)",
        "bands": ["Green", "SWIR1"],
        "range": "[-1, 1]",
        "description": "改进水体指数（Xu 2006），比NDWI更好区分水体与建筑阴影，城市区域推荐使用。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: safe_div(b["Green"] - b["SWIR1"], b["Green"] + b["SWIR1"]),
    },
    "AWEI_nsh": {
        "full_name": "Automated Water Extraction Index (no shadow)",
        "formula_display": "4*(Green-SWIR1)-(0.25*NIR+2.75*SWIR2)",
        "bands": ["Green", "NIR", "SWIR1", "SWIR2"],
        "range": "[-∞, +∞]",
        "description": "自动水体提取指数（无阴影版），>0 为水体，复杂环境下优于MNDWI。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: 4*(b["Green"] - b["SWIR1"]) - (0.25*b["NIR"] + 2.75*b["SWIR2"]),
    },
    "AWEI_sh": {
        "full_name": "Automated Water Extraction Index (shadow)",
        "formula_display": "Blue+2.5*Green-1.5*(NIR+SWIR1)-0.25*SWIR2",
        "bands": ["Blue", "Green", "NIR", "SWIR1", "SWIR2"],
        "range": "[-∞, +∞]",
        "description": "自动水体提取指数（含阴影版），可有效消除城市阴影干扰。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: b["Blue"] + 2.5*b["Green"] - 1.5*(b["NIR"] + b["SWIR1"]) - 0.25*b["SWIR2"],
    },
    "WRI": {
        "full_name": "Water Ratio Index",
        "formula_display": "(Green+Red)/(NIR+SWIR1)",
        "bands": ["Green", "Red", "NIR", "SWIR1"],
        "range": "[0, ∞)",
        "description": "水体比率指数，>1 通常为水体，对浅水和浑浊水体有一定效果。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: safe_div(b["Green"] + b["Red"], b["NIR"] + b["SWIR1"]),
    },
    "NDMI": {
        "full_name": "Normalized Difference Moisture Index",
        "formula_display": "(NIR-SWIR1)/(NIR+SWIR1)",
        "bands": ["NIR", "SWIR1"],
        "range": "[-1, 1]",
        "description": "植被水分含量指数，监测植被水分胁迫，正值为湿润植被，也用于土壤水分估算。",
        "category": "Water",
        "colormap": "Blues",
        "func": lambda b: safe_div(b["NIR"] - b["SWIR1"], b["NIR"] + b["SWIR1"]),
    },

    # ── 城市建筑 Urban ───────────────────────────────
    "NDBI": {
        "full_name": "Normalized Difference Built-up Index",
        "formula_display": "(SWIR1-NIR)/(SWIR1+NIR)",
        "bands": ["SWIR1", "NIR"],
        "range": "[-1, 1]",
        "description": "建筑用地指数，>0 为建筑区域。常与MNDWI、NDVI组合用于城市土地覆盖分类。",
        "category": "Urban",
        "colormap": "hot",
        "func": lambda b: safe_div(b["SWIR1"] - b["NIR"], b["SWIR1"] + b["NIR"]),
    },
    "UI": {
        "full_name": "Urban Index",
        "formula_display": "(SWIR2-NIR)/(SWIR2+NIR)",
        "bands": ["SWIR2", "NIR"],
        "range": "[-1, 1]",
        "description": "城市指数，用于城市扩张制图，对建成区具有较强响应。",
        "category": "Urban",
        "colormap": "hot",
        "func": lambda b: safe_div(b["SWIR2"] - b["NIR"], b["SWIR2"] + b["NIR"]),
    },
    "IBI": {
        "full_name": "Index-based Built-up Index",
        "formula_display": "(NDBI-(SAVI+MNDWI)/2)/(NDBI+(SAVI+MNDWI)/2)",
        "bands": ["NIR", "Red", "SWIR1", "Green"],
        "range": "[-1, 1]",
        "description": "综合建筑指数，结合NDBI、SAVI和MNDWI，有效抑制植被和水体，城市提取精度高。",
        "category": "Urban",
        "colormap": "hot",
        "func": lambda b: (
            lambda ndbi, savi, mndwi:
            safe_div(ndbi - (savi + mndwi)/2, ndbi + (savi + mndwi)/2)
        )(
            safe_div(b["SWIR1"]-b["NIR"], b["SWIR1"]+b["NIR"]),
            1.5*safe_div(b["NIR"]-b["Red"], b["NIR"]+b["Red"]+0.5),
            safe_div(b["Green"]-b["SWIR1"], b["Green"]+b["SWIR1"])
        ),
    },

    # ── 土壤 Soil ────────────────────────────────────
    "BSI": {
        "full_name": "Bare Soil Index",
        "formula_display": "((SWIR1+Red)-(NIR+Blue))/((SWIR1+Red)+(NIR+Blue))",
        "bands": ["SWIR1", "Red", "NIR", "Blue"],
        "range": "[-1, 1]",
        "description": "裸土指数，识别裸土与土地退化区域，正值表示裸土。",
        "category": "Soil",
        "colormap": "YlOrBr",
        "func": lambda b: safe_div(
            (b["SWIR1"]+b["Red"]) - (b["NIR"]+b["Blue"]),
            (b["SWIR1"]+b["Red"]) + (b["NIR"]+b["Blue"])
        ),
    },
    "RI": {
        "full_name": "Redness Index",
        "formula_display": "Red²/(Blue*NIR³)",
        "bands": ["Red", "Blue", "NIR"],
        "range": "[0, ∞)",
        "description": "红色指数，反映土壤氧化铁含量，值越高土壤越红，可用于土壤类型制图。",
        "category": "Soil",
        "colormap": "YlOrBr",
        "func": lambda b: safe_div(b["Red"]**2, b["Blue"] * b["NIR"]**3),
    },
    "SATVI": {
        "full_name": "Soil-Adjusted Total Vegetation Index",
        "formula_display": "((SWIR1-Red)/(SWIR1+Red+0.5))*1.5 - SWIR2/2",
        "bands": ["SWIR1", "Red", "SWIR2"],
        "range": "[-∞, +∞]",
        "description": "土壤调整总植被指数，同时考虑光合和非光合植被，适用于稀疏植被和草地覆盖制图。",
        "category": "Soil",
        "colormap": "YlOrBr",
        "func": lambda b: 1.5*safe_div(b["SWIR1"]-b["Red"], b["SWIR1"]+b["Red"]+0.5) - b["SWIR2"]/2,
    },

    # ── 积雪/冰 Snow/Ice ─────────────────────────────
    "NDSI": {
        "full_name": "Normalized Difference Snow Index",
        "formula_display": "(Green-SWIR1)/(Green+SWIR1)",
        "bands": ["Green", "SWIR1"],
        "range": "[-1, 1]",
        "description": "积雪指数，>0.4 通常为积雪，可与NDVI组合区分云和雪。",
        "category": "Snow/Ice",
        "colormap": "cool",
        "func": lambda b: safe_div(b["Green"] - b["SWIR1"], b["Green"] + b["SWIR1"]),
    },

    # ── 火灾 Fire ────────────────────────────────────
    "NBR": {
        "full_name": "Normalized Burn Ratio",
        "formula_display": "(NIR-SWIR2)/(NIR+SWIR2)",
        "bands": ["NIR", "SWIR2"],
        "range": "[-1, 1]",
        "description": "归一化燃烧比，用于评估火灾烈度，健康植被>0.3，火烧迹地<0，dNBR=火前-火后用于评估损失等级。",
        "category": "Fire",
        "colormap": "RdBu",
        "func": lambda b: safe_div(b["NIR"] - b["SWIR2"], b["NIR"] + b["SWIR2"]),
    },
    "NBR2": {
        "full_name": "Normalized Burn Ratio 2",
        "formula_display": "(SWIR1-SWIR2)/(SWIR1+SWIR2)",
        "bands": ["SWIR1", "SWIR2"],
        "range": "[-1, 1]",
        "description": "第二燃烧比，对火烧后土壤湿度变化敏感，与NBR互补使用。",
        "category": "Fire",
        "colormap": "RdBu",
        "func": lambda b: safe_div(b["SWIR1"] - b["SWIR2"], b["SWIR1"] + b["SWIR2"]),
    },
    "BAI": {
        "full_name": "Burned Area Index",
        "formula_display": "1/((0.1-Red)²+(0.06-NIR)²)",
        "bands": ["Red", "NIR"],
        "range": "[0, ∞)",
        "description": "火烧迹地指数，高值对应近期火烧区域，对火烧面积评估敏感。",
        "category": "Fire",
        "colormap": "RdBu",
        "func": lambda b: safe_div(1.0, (0.1 - b["Red"])**2 + (0.06 - b["NIR"])**2),
    },

    # ── 干旱 Drought ─────────────────────────────────
    "NDDI": {
        "full_name": "Normalized Difference Drought Index",
        "formula_display": "(NDVI-NDWI)/(NDVI+NDWI)",
        "bands": ["NIR", "Red", "Green"],
        "range": "[-1, 1]",
        "description": "归一化干旱指数，结合植被和水分信息，比单独使用NDVI对干旱更敏感。",
        "category": "Drought",
        "colormap": "RdYlBu",
        "func": lambda b: (
            lambda ndvi, ndwi: safe_div(ndvi - ndwi, ndvi + ndwi)
        )(
            safe_div(b["NIR"]-b["Red"], b["NIR"]+b["Red"]),
            safe_div(b["Green"]-b["NIR"], b["Green"]+b["NIR"])
        ),
    },
    "NMDI": {
        "full_name": "Normalized Multi-band Drought Index",
        "formula_display": "(NIR-(SWIR1-SWIR2))/(NIR+(SWIR1-SWIR2))",
        "bands": ["NIR", "SWIR1", "SWIR2"],
        "range": "[-1, 1]",
        "description": "多波段归一化干旱指数，同时响应土壤和植被含水量，用于旱情监测。",
        "category": "Drought",
        "colormap": "RdYlBu",
        "func": lambda b: safe_div(
            b["NIR"] - (b["SWIR1"] - b["SWIR2"]),
            b["NIR"] + (b["SWIR1"] - b["SWIR2"])
        ),
    },

    # ── 地表温度/热岛 Thermal ────────────────────────
    "NDLST": {
        "full_name": "Normalized Difference Land Surface Temperature Index",
        "formula_display": "(TIR1-TIR2)/(TIR1+TIR2)",
        "bands": ["TIR1", "TIR2"],
        "range": "[-1, 1]",
        "description": "热波段差值指数，辅助地表温度分析，需Landsat 8/9 TIR波段。",
        "category": "Thermal",
        "colormap": "inferno",
        "func": lambda b: safe_div(b["TIR1"] - b["TIR2"], b["TIR1"] + b["TIR2"]),
    },
}

CATEGORIES = ["All"] + sorted(set(v["category"] for v in INDEX_DEFINITIONS.values()))

# 色彩方案配置
COLORMAPS = {
    "RdYlGn": {"vmin": -1, "vmax": 1},
    "Blues":   {"vmin": -1, "vmax": 1},
    "hot":     {"vmin": -1, "vmax": 1},
    "YlOrBr":  {"vmin": -1, "vmax": 1},
    "cool":    {"vmin": -1, "vmax": 1},
    "RdBu":    {"vmin": -1, "vmax": 1},
    "RdYlBu":  {"vmin": -1, "vmax": 1},
    "inferno": {"vmin":  0, "vmax": 1},
}


# ══════════════════════════════════════════════════════
#  自定义指数管理
# ══════════════════════════════════════════════════════
CUSTOM_INDEX_FILE = "custom_indices.json"

def load_custom_indices():
    if os.path.exists(CUSTOM_INDEX_FILE):
        try:
            with open(CUSTOM_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_custom_indices(custom_dict):
    with open(CUSTOM_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(custom_dict, f, ensure_ascii=False, indent=2)

def _parse_envi_hdr_band_names(hdr_path):
    """解析 ENVI .hdr 文件中的 band names 字段，返回列表"""
    try:
        with open(hdr_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        import re
        # band names = {B1, B2, ...} 可能跨行
        m = re.search(r"band names\s*=\s*\{([^}]+)\}", text, re.IGNORECASE | re.DOTALL)
        if m:
            raw = m.group(1)
            names = [n.strip() for n in raw.split(",") if n.strip()]
            return names
    except Exception:
        pass
    return []


def eval_custom_formula(formula_str, band_data):
    """安全地计算自定义公式"""
    allowed_names = {k: v for k, v in band_data.items()}
    allowed_names.update({
        "np": np, "sqrt": np.sqrt, "abs": np.abs,
        "log": np.log, "exp": np.exp, "nan": np.nan
    })
    result = eval(compile(formula_str, "<formula>", "eval"), {"__builtins__": {}}, allowed_names)
    return result.astype(np.float32)


# ══════════════════════════════════════════════════════
#  主应用
# ══════════════════════════════════════════════════════
class RSCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RS Index Calculator v2.0")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.root.configure(bg="#0D1117")

        self.input_files = []
        self.output_dir = tk.StringVar()
        self.selected_sensor = tk.StringVar(value="Landsat 8/9 (OLI)")
        self.selected_indices = {}
        self.band_vars = {}
        self.nodata_val = tk.StringVar(value="0")
        self.scale_factor = tk.StringVar(value="1.0")
        self.filter_category = tk.StringVar(value="All")
        self.output_format = tk.StringVar(value="GeoTIFF (.tif)")
        self.custom_indices = load_custom_indices()
        # 智能导入状态
        self._smart_band_files = {}   # {逻辑波段名: 文件路径}，智能导入后填充
        self._smart_scene_id   = ""
        self._smart_offset     = 0.0

        # 预览相关
        self.preview_result = None
        self.preview_name = ""

        self._setup_styles()
        self._build_ui()
        self._refresh_index_list()

    # ── 样式 ─────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        C = {
            "BG": "#0D1117", "PANEL": "#161B22", "BORDER": "#30363D",
            "ACCENT": "#00D4A1", "TEXT": "#E6EDF3", "MUTED": "#8B949E",
            "SEL": "#1C2A23",
        }
        self.C = C
        for name, opts in [
            (".", dict(background=C["BG"], foreground=C["TEXT"], font=("Consolas", 10))),
            ("TFrame", dict(background=C["BG"])),
            ("TLabel", dict(background=C["BG"], foreground=C["TEXT"])),
            ("TButton", dict(background=C["PANEL"], foreground=C["TEXT"],
                             bordercolor=C["BORDER"], padding=(8,5))),
            ("Accent.TButton", dict(background=C["ACCENT"], foreground="#0D1117",
                                    font=("Consolas", 10, "bold"), padding=(12,7))),
            ("TCombobox", dict(fieldbackground=C["PANEL"], background=C["PANEL"],
                               foreground=C["TEXT"], selectbackground=C["SEL"],
                               arrowcolor=C["ACCENT"], bordercolor=C["BORDER"])),
            ("TEntry", dict(fieldbackground=C["PANEL"], foreground=C["TEXT"],
                            insertcolor=C["TEXT"], bordercolor=C["BORDER"])),
            ("TCheckbutton", dict(background=C["PANEL"], foreground=C["TEXT"])),
            ("TScrollbar", dict(background=C["PANEL"], troughcolor=C["BG"],
                                arrowcolor=C["MUTED"])),
            ("TNotebook", dict(background=C["BG"], bordercolor=C["BORDER"])),
            ("TNotebook.Tab", dict(background=C["PANEL"], foreground=C["MUTED"], padding=(12,6))),
            ("Treeview", dict(background=C["PANEL"], fieldbackground=C["PANEL"],
                              foreground=C["TEXT"], rowheight=26)),
            ("Treeview.Heading", dict(background=C["BG"], foreground=C["MUTED"])),
        ]:
            s.configure(name, **opts)

        s.map("TButton", background=[("active", C["SEL"])], foreground=[("active", C["ACCENT"])])
        s.map("Accent.TButton", background=[("active", "#00B88A")])
        s.map("TCheckbutton", indicatorcolor=[("selected", C["ACCENT"]), ("!selected", C["BORDER"])])
        s.map("TNotebook.Tab", background=[("selected", C["BG"])], foreground=[("selected", C["ACCENT"])])
        s.map("TCombobox", fieldbackground=[("readonly", C["PANEL"])])
        s.map("Treeview", background=[("selected", C["SEL"])], foreground=[("selected", C["ACCENT"])])

    # ── UI 构建 ───────────────────────────────────────
    def _build_ui(self):
        C = self.C
        hdr = tk.Frame(self.root, bg=C["BG"], pady=10)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="◈ RS INDEX CALCULATOR", bg=C["BG"], fg=C["ACCENT"],
                 font=("Consolas", 16, "bold")).pack(side="left")
        tk.Label(hdr, text="v2.0  |  Landsat · Sentinel · MODIS  |  30+ Indices",
                 bg=C["BG"], fg=C["MUTED"], font=("Consolas", 9)).pack(side="left", padx=14)

        tk.Frame(self.root, bg=C["BORDER"], height=1).pack(fill="x", padx=20)

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=15, pady=8)

        self.tab_main    = ttk.Frame(nb)
        self.tab_custom  = ttk.Frame(nb)
        self.tab_band    = ttk.Frame(nb)
        self.tab_prev    = ttk.Frame(nb)
        self.tab_log     = ttk.Frame(nb)
        self.tab_datasrc = ttk.Frame(nb)

        nb.add(self.tab_main,   text="  ① 数据 & 指数  ")
        nb.add(self.tab_custom, text="  ② 自定义指数  ")
        nb.add(self.tab_band,   text="  ③ 波段映射  ")
        nb.add(self.tab_prev,   text="  ④ 结果预览  ")
        nb.add(self.tab_log,    text="  ⑤ 运行日志  ")
        nb.add(self.tab_datasrc, text="  ⑥ 数据来源  ")
        self.notebook = nb

        self._build_main_tab()
        self._build_custom_tab()
        self._build_band_tab()
        self._build_preview_tab()
        self._build_log_tab()
        self._build_datasrc_tab()
        self._build_run_bar()

    # ── Tab 1: 主页 ───────────────────────────────────
    def _build_main_tab(self):
        C = self.C
        f = self.tab_main

        left = tk.Frame(f, bg=C["BG"], width=330)
        left.pack(side="left", fill="y", padx=(5,5), pady=5)
        left.pack_propagate(False)

        def panel(parent, label=None):
            p = tk.Frame(parent, bg=C["PANEL"], bd=0,
                         highlightbackground=C["BORDER"], highlightthickness=1)
            p.pack(fill="x", padx=5, pady=3)
            if label:
                tk.Label(p, text=f"  {label}", bg=C["PANEL"], fg=C["MUTED"],
                         font=("Consolas", 9)).pack(anchor="w", padx=8, pady=(8,2))
            return p

        # Sensor
        sp = panel(left, "传感器类型")
        cb = ttk.Combobox(sp, textvariable=self.selected_sensor,
                          values=list(SENSOR_BANDS.keys()), state="readonly", width=36)
        cb.pack(padx=8, pady=(0,8))
        cb.bind("<<ComboboxSelected>>", self._on_sensor_change)

        # Files
        fp = tk.Frame(left, bg=C["PANEL"], bd=0,
                      highlightbackground=C["BORDER"], highlightthickness=1)
        fp.pack(fill="both", expand=True, padx=5, pady=3)
        tk.Label(fp, text="  输入文件", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(anchor="w", padx=8, pady=(8,4))

        br = tk.Frame(fp, bg=C["PANEL"])
        br.pack(fill="x", padx=8, pady=(0,4))
        ttk.Button(br, text="+ 添加", width=7, command=self._add_files).pack(side="left", padx=2)
        ttk.Button(br, text="清空",   width=6, command=self._clear_files).pack(side="left", padx=2)
        ttk.Button(br, text="⚡ 智能导入", command=self._smart_import).pack(side="left", padx=(6,0))

        self.file_list = tk.Listbox(fp, bg=C["PANEL"], fg=C["TEXT"],
                                     selectbackground=C["BORDER"], selectforeground=C["ACCENT"],
                                     borderwidth=0, highlightthickness=0,
                                     font=("Consolas", 9), activestyle="none")
        sc = ttk.Scrollbar(fp, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y", padx=(0,4), pady=4)
        self.file_list.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Output
        op = panel(left, "输出路径")
        orow = tk.Frame(op, bg=C["PANEL"])
        orow.pack(fill="x", padx=8, pady=(0,8))
        ttk.Entry(orow, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(orow, text="浏览", width=6, command=self._browse_output).pack(side="left", padx=(4,0))

        # Options row
        xp = panel(left)
        xrow = tk.Frame(xp, bg=C["PANEL"])
        xrow.pack(fill="x", padx=8, pady=(8,4))
        tk.Label(xrow, text="NoData:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Entry(xrow, textvariable=self.nodata_val, width=6).pack(side="left", padx=(3,12))
        tk.Label(xrow, text="缩放:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Entry(xrow, textvariable=self.scale_factor, width=8).pack(side="left", padx=(3,0))

        # Output format row
        fmtrow = tk.Frame(xp, bg=C["PANEL"])
        fmtrow.pack(fill="x", padx=8, pady=(0,8))
        tk.Label(fmtrow, text="输出格式:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Combobox(fmtrow, textvariable=self.output_format,
                     values=[
                         "GeoTIFF (.tif)",
                         "ENVI (.img + .hdr)",
                         "ENVI (.dat + .hdr)",
                     ],
                     state="readonly", width=22).pack(side="left", padx=(6, 0))


        # Right: index list
        right = tk.Frame(f, bg=C["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(0,5), pady=5)

        # Filter row
        fr = tk.Frame(right, bg=C["PANEL"], bd=0,
                      highlightbackground=C["BORDER"], highlightthickness=1)
        fr.pack(fill="x", padx=5, pady=(5,3))
        frow = tk.Frame(fr, bg=C["PANEL"])
        frow.pack(padx=8, pady=6, fill="x")
        tk.Label(frow, text="类别:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        cat_cb = ttk.Combobox(frow, textvariable=self.filter_category,
                               values=CATEGORIES, state="readonly", width=14)
        cat_cb.pack(side="left", padx=(4,12))
        cat_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_index_list())
        ttk.Button(frow, text="全选", width=6, command=self._select_all).pack(side="left", padx=2)
        ttk.Button(frow, text="全清", width=6, command=self._deselect_all).pack(side="left")

        # Count label
        self.count_label = tk.Label(frow, text="", bg=C["PANEL"], fg=C["ACCENT"],
                                     font=("Consolas", 9))
        self.count_label.pack(side="right", padx=8)

        # Index scroll area
        ip = tk.Frame(right, bg=C["PANEL"], bd=0,
                      highlightbackground=C["BORDER"], highlightthickness=1)
        ip.pack(fill="both", expand=True, padx=5, pady=3)

        canvas = tk.Canvas(ip, bg=C["PANEL"], borderwidth=0, highlightthickness=0)
        vs = ttk.Scrollbar(ip, orient="vertical", command=canvas.yview)
        self.idx_inner = tk.Frame(canvas, bg=C["PANEL"])
        self.idx_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.idx_inner, anchor="nw")
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Info bar
        self.info_bar = tk.Label(right, text="← 鼠标悬停指数行查看公式与说明",
                                  bg=C["PANEL"], fg=C["MUTED"],
                                  font=("Consolas", 9), anchor="w",
                                  justify="left", wraplength=420,
                                  pady=7, padx=10,
                                  highlightbackground=C["BORDER"], highlightthickness=1)
        self.info_bar.pack(fill="x", padx=5, pady=3)

    # ── Tab 2: 自定义指数 ─────────────────────────────
    def _build_custom_tab(self):
        C = self.C
        f = self.tab_custom

        tk.Label(f, text="自定义公式规则：使用波段名称（如 NIR, Red, Green, Blue, SWIR1, SWIR2...）直接写 Python/NumPy 表达式",
                 bg=C["BG"], fg=C["MUTED"], font=("Consolas", 9),
                 wraplength=700, justify="left").pack(anchor="w", padx=15, pady=(12,4))
        tk.Label(f, text='示例：(NIR - Red) / (NIR + Red)     |     np.sqrt(NIR) - Red     |     (Green + NIR) / (SWIR1 + 1)',
                 bg=C["BG"], fg=C["ACCENT"], font=("Consolas", 9)).pack(anchor="w", padx=15, pady=(0,8))

        form = tk.Frame(f, bg=C["PANEL"], bd=0,
                        highlightbackground=C["BORDER"], highlightthickness=1)
        form.pack(fill="x", padx=15, pady=4)

        def row(label, var_or_widget, width=30):
            r = tk.Frame(form, bg=C["PANEL"])
            r.pack(fill="x", padx=12, pady=5)
            tk.Label(r, text=label, bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas", 9), width=12, anchor="e").pack(side="left", padx=(0,8))
            if isinstance(var_or_widget, tk.Variable):
                ttk.Entry(r, textvariable=var_or_widget, width=width).pack(side="left", fill="x", expand=True)
            else:
                var_or_widget.pack(side="left", fill="x", expand=True)
            return r

        self.cv_name    = tk.StringVar()
        self.cv_full    = tk.StringVar()
        self.cv_formula = tk.StringVar()
        self.cv_bands   = tk.StringVar()
        self.cv_desc    = tk.StringVar()
        self.cv_cat     = tk.StringVar(value="Custom")
        self.cv_cmap    = tk.StringVar(value="RdYlGn")

        tk.Frame(form, bg=C["PANEL"], height=8).pack()
        row("缩写名称:", self.cv_name, 16)
        row("全称:", self.cv_full, 40)
        row("公式:", self.cv_formula, 50)
        row("所需波段:", self.cv_bands)
        tk.Label(form, text="   (逗号分隔, 如: NIR,Red,Green)",
                 bg=C["PANEL"], fg=C["MUTED"], font=("Consolas", 8)).pack(anchor="w", padx=12)
        row("描述:", self.cv_desc, 50)

        cmap_row = tk.Frame(form, bg=C["PANEL"])
        cmap_row.pack(fill="x", padx=12, pady=5)
        tk.Label(cmap_row, text="色彩方案:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9), width=12, anchor="e").pack(side="left", padx=(0,8))
        ttk.Combobox(cmap_row, textvariable=self.cv_cmap,
                     values=list(COLORMAPS.keys()), state="readonly", width=14).pack(side="left")
        tk.Frame(form, bg=C["PANEL"], height=8).pack()

        btn_row = tk.Frame(form, bg=C["PANEL"])
        btn_row.pack(fill="x", padx=12, pady=(0,10))
        ttk.Button(btn_row, text="▶ 测试公式", command=self._test_formula).pack(side="left", padx=(0,6))
        ttk.Button(btn_row, text="+ 添加到列表", style="Accent.TButton",
                   command=self._add_custom_index).pack(side="left")

        self.formula_test_label = tk.Label(form, text="", bg=C["PANEL"], fg=C["MUTED"],
                                            font=("Consolas", 9))
        self.formula_test_label.pack(anchor="w", padx=12, pady=(0,6))

        # 已保存的自定义指数列表
        tk.Label(f, text="已添加的自定义指数:", bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(anchor="w", padx=15, pady=(10,2))

        list_frame = tk.Frame(f, bg=C["PANEL"], bd=0,
                               highlightbackground=C["BORDER"], highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0,10))

        cols = ("name", "formula", "bands")
        self.custom_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=6)
        self.custom_tree.heading("name",    text="名称")
        self.custom_tree.heading("formula", text="公式")
        self.custom_tree.heading("bands",   text="波段需求")
        self.custom_tree.column("name",    width=80)
        self.custom_tree.column("formula", width=320)
        self.custom_tree.column("bands",   width=160)
        csb = ttk.Scrollbar(list_frame, orient="vertical", command=self.custom_tree.yview)
        self.custom_tree.configure(yscrollcommand=csb.set)
        csb.pack(side="right", fill="y")
        self.custom_tree.pack(fill="both", expand=True)

        del_row = tk.Frame(f, bg=C["BG"])
        del_row.pack(fill="x", padx=15, pady=(0,8))
        ttk.Button(del_row, text="删除选中", command=self._delete_custom_index).pack(side="right")

        self._refresh_custom_tree()

    def _test_formula(self):
        formula = self.cv_formula.get().strip()
        if not formula:
            return
        try:
            # 用随机数测试
            dummy = {k: np.random.rand(4, 4).astype(np.float32)
                     for k in ["NIR", "Red", "Green", "Blue", "SWIR1", "SWIR2",
                                "SWIR3", "RedEdge1", "RedEdge2", "RedEdge3",
                                "Coastal", "PAN", "TIR", "TIR1", "TIR2"]}
            result = eval_custom_formula(formula, dummy)
            mn, mx = float(np.nanmin(result)), float(np.nanmax(result))
            self.formula_test_label.configure(
                text=f"✓ 公式有效  测试值域: [{mn:.3f}, {mx:.3f}]",
                fg=self.C["ACCENT"])
        except Exception as e:
            self.formula_test_label.configure(
                text=f"✗ 公式错误: {str(e)}", fg="#FF6B6B")

    def _add_custom_index(self):
        name    = self.cv_name.get().strip().upper()
        full    = self.cv_full.get().strip()
        formula = self.cv_formula.get().strip()
        bands   = [b.strip() for b in self.cv_bands.get().split(",") if b.strip()]
        desc    = self.cv_desc.get().strip()
        cmap    = self.cv_cmap.get()

        if not name or not formula or not bands:
            messagebox.showwarning("提示", "名称、公式和所需波段不能为空！")
            return

        self.custom_indices[name] = {
            "full_name": full or name,
            "formula_display": formula,
            "bands": bands,
            "description": desc,
            "colormap": cmap,
            "category": "Custom",
        }
        save_custom_indices(self.custom_indices)
        self._refresh_custom_tree()
        self._refresh_index_list()
        self.formula_test_label.configure(text=f"✓ 已添加 {name}", fg=self.C["ACCENT"])

    def _delete_custom_index(self):
        sel = self.custom_tree.selection()
        if not sel:
            return
        name = self.custom_tree.item(sel[0])["values"][0]
        if name in self.custom_indices:
            del self.custom_indices[name]
            save_custom_indices(self.custom_indices)
            self._refresh_custom_tree()
            self._refresh_index_list()

    def _refresh_custom_tree(self):
        for item in self.custom_tree.get_children():
            self.custom_tree.delete(item)
        for name, d in self.custom_indices.items():
            self.custom_tree.insert("", "end", values=(
                name, d["formula_display"], ", ".join(d["bands"])
            ))

    # ── Tab 3: 波段映射 ───────────────────────────────
    def _build_band_tab(self):
        C = self.C
        f = self.tab_band
        self.band_tab_inner = tk.Frame(f, bg=C["BG"])
        self.band_tab_inner.pack(fill="both", expand=True, padx=15, pady=10)
        self._refresh_band_config()

    def _refresh_band_config(self):
        C = self.C
        for w in self.band_tab_inner.winfo_children():
            w.destroy()
        self.band_vars.clear()

        sensor = self.selected_sensor.get()
        bands  = SENSOR_BANDS.get(sensor, {})

        tk.Label(self.band_tab_inner,
                 text=f"传感器: {sensor}　—　逻辑波段名 → 实际波段编号",
                 bg=C["BG"], fg=C["ACCENT"],
                 font=("Consolas", 11, "bold")).pack(anchor="w", pady=(0,8))

        grid = tk.Frame(self.band_tab_inner, bg=C["BG"])
        grid.pack(anchor="w")

        for col, h in enumerate(["波段名称", "波长范围", "默认编号", "自定义编号"]):
            tk.Label(grid, text=h, bg=C["BG"], fg=C["MUTED"],
                     font=("Consolas", 9), width=16, anchor="w").grid(
                         row=0, column=col, padx=6, pady=2)

        for ri, (bname, binfo) in enumerate(bands.items(), 1):
            tk.Label(grid, text=bname, bg=C["BG"], fg=C["TEXT"],
                     font=("Consolas", 9), anchor="w", width=14).grid(row=ri, column=0, padx=6, pady=3)
            tk.Label(grid, text=binfo["wavelength"], bg=C["BG"], fg=C["MUTED"],
                     font=("Consolas", 8), anchor="w", width=16).grid(row=ri, column=1, padx=6)
            tk.Label(grid, text=str(binfo["band"]), bg=C["BG"], fg=C["ACCENT"],
                     font=("Consolas", 9), anchor="w", width=10).grid(row=ri, column=2, padx=6)
            var = tk.StringVar(value=str(binfo["band"]))
            self.band_vars[bname] = var
            ttk.Entry(grid, textvariable=var, width=8).grid(row=ri, column=3, padx=6)

        opt_p = tk.Frame(self.band_tab_inner, bg=C["PANEL"], bd=0,
                         highlightbackground=C["BORDER"], highlightthickness=1)
        opt_p.pack(fill="x", pady=12)
        orow = tk.Frame(opt_p, bg=C["PANEL"])
        orow.pack(padx=12, pady=10, fill="x")
        tk.Label(orow, text="NoData 值:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Entry(orow, textvariable=self.nodata_val, width=8).pack(side="left", padx=(4,20))
        tk.Label(orow, text="缩放系数:", bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Entry(orow, textvariable=self.scale_factor, width=8).pack(side="left", padx=4)
        tk.Label(orow, text="(Landsat L2 Collection 2 = 2.75e-5, offset = -0.2)",
                 bg=C["PANEL"], fg=C["MUTED"], font=("Consolas", 8)).pack(side="left", padx=6)

    # ── Tab 4: 结果预览 ───────────────────────────────
    def _build_preview_tab(self):
        C = self.C
        f = self.tab_prev

        ctrl = tk.Frame(f, bg=C["BG"])
        ctrl.pack(fill="x", padx=15, pady=(10,4))

        tk.Label(ctrl, text="选择结果文件预览:", bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(side="left")
        ttk.Button(ctrl, text="打开 .tif 预览",
                   command=self._open_preview_file).pack(side="left", padx=8)

        self.prev_colormap = tk.StringVar(value="RdYlGn")
        ttk.Combobox(ctrl, textvariable=self.prev_colormap,
                     values=list(COLORMAPS.keys()), state="readonly", width=12).pack(side="left", padx=4)
        ttk.Button(ctrl, text="刷新色彩", command=self._refresh_preview).pack(side="left", padx=4)

        self.prev_info = tk.Label(ctrl, text="", bg=C["BG"], fg=C["MUTED"],
                                   font=("Consolas", 9))
        self.prev_info.pack(side="right", padx=10)

        # 预览区
        self.prev_frame = tk.Frame(f, bg=C["PANEL"], bd=0,
                                    highlightbackground=C["BORDER"], highlightthickness=1)
        self.prev_frame.pack(fill="both", expand=True, padx=15, pady=(0,10))

        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(8, 5), facecolor="#161B22")
            self.ax  = self.fig.add_subplot(111)
            self.ax.set_facecolor("#0D1117")
            self.ax.tick_params(colors="#8B949E")
            for spine in self.ax.spines.values():
                spine.set_edgecolor("#30363D")
            self.canvas_mpl = FigureCanvasTkAgg(self.fig, master=self.prev_frame)
            self.canvas_mpl.get_tk_widget().pack(fill="both", expand=True)
        else:
            tk.Label(self.prev_frame,
                     text="请安装 matplotlib 以启用预览功能\npip install matplotlib",
                     bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas", 11)).pack(expand=True)

    def _open_preview_file(self):
        path = filedialog.askopenfilename(
            title="选择结果文件",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("All", "*.*")]
        )
        if path and RASTERIO_AVAILABLE and MATPLOTLIB_AVAILABLE:
            try:
                with rasterio.open(path) as src:
                    self.preview_result = src.read(1).astype(np.float32)
                    self.preview_name   = Path(path).name
                self._refresh_preview()
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def _refresh_preview(self):
        if self.preview_result is None or not MATPLOTLIB_AVAILABLE:
            return
        data = self.preview_result.copy()
        cmap = self.prev_colormap.get()

        self.ax.clear()
        self.ax.set_facecolor("#0D1117")
        self.ax.tick_params(colors="#8B949E")

        vmin = np.nanpercentile(data, 2)
        vmax = np.nanpercentile(data, 98)

        im = self.ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        self.fig.colorbar(im, ax=self.ax, fraction=0.03, pad=0.02).ax.tick_params(colors="#8B949E")

        valid = data[~np.isnan(data)]
        self.ax.set_title(self.preview_name, color="#E6EDF3", fontsize=10, pad=8)
        self.prev_info.configure(
            text=f"min={np.nanmin(data):.3f}  max={np.nanmax(data):.3f}  mean={np.nanmean(data):.3f}  "
                 f"size={data.shape[0]}×{data.shape[1]}"
        )

        for spine in self.ax.spines.values():
            spine.set_edgecolor("#30363D")

        self.canvas_mpl.draw()
        self.notebook.select(self.tab_prev)

    # ── Tab 5: 日志 ───────────────────────────────────
    def _build_log_tab(self):
        C = self.C
        f = self.tab_log
        ctrl = tk.Frame(f, bg=C["BG"])
        ctrl.pack(fill="x", padx=15, pady=(10,4))
        ttk.Button(ctrl, text="清除日志", command=self._clear_log).pack(side="right")
        self.log_text = scrolledtext.ScrolledText(
            f, bg=C["PANEL"], fg=C["TEXT"], insertbackground=C["TEXT"],
            font=("Consolas", 9), borderwidth=0, highlightthickness=0, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0,10))
        for tag, color in [("info", C["TEXT"]), ("success", C["ACCENT"]),
                            ("warning", "#FFB347"), ("error", "#FF6B6B"),
                            ("header", C["ACCENT"])]:
            self.log_text.tag_configure(tag, foreground=color,
                font=("Consolas", 9, "bold") if tag == "header" else ("Consolas", 9))

    # ── Tab 6: 数据来源 ──────────────────────────────
    def _build_datasrc_tab(self):
        if DATA_SOURCES_AVAILABLE:
            build_data_source_tab(self.tab_datasrc, self.C)
        else:
            tk.Label(self.tab_datasrc,
                     text="data_sources.py 未找到，请将其与主程序放在同一目录",
                     bg=self.C["BG"], fg=self.C["MUTED"],
                     font=("Consolas", 10)).pack(expand=True)

    # ── Run bar ───────────────────────────────────────
    def _build_run_bar(self):
        C = self.C
        bar = tk.Frame(self.root, bg=C["PANEL"],
                       highlightbackground=C["BORDER"], highlightthickness=1)
        bar.pack(fill="x", padx=15, pady=(0,12))
        inner = tk.Frame(bar, bg=C["PANEL"])
        inner.pack(fill="x", padx=12, pady=8)
        self.status_label = tk.Label(inner, text="就绪", bg=C["PANEL"], fg=C["MUTED"],
                                      font=("Consolas", 9))
        self.status_label.pack(side="left")
        self.progress = ttk.Progressbar(inner, mode="determinate", length=200)
        self.progress.pack(side="left", padx=15)
        ttk.Button(inner, text="▶  开始计算", style="Accent.TButton",
                   command=self._run_calculation).pack(side="right")

    # ── 指数列表 ──────────────────────────────────────
    def _refresh_index_list(self):
        for w in self.idx_inner.winfo_children():
            w.destroy()
        self.selected_indices.clear()

        C = self.C
        cat    = self.filter_category.get()
        sensor = self.selected_sensor.get()
        avail  = set(SENSOR_BANDS.get(sensor, {}).keys())

        # 合并内置 + 自定义
        all_indices = dict(INDEX_DEFINITIONS)
        for k, v in self.custom_indices.items():
            all_indices[k] = {**v, "func": None}

        cur_cat = None
        count = 0
        for name, defn in all_indices.items():
            if cat != "All" and defn["category"] != cat:
                continue

            if defn["category"] != cur_cat:
                cur_cat = defn["category"]
                tag_colors = {
                    "Vegetation": "#00D4A1", "Water": "#4FC3F7",
                    "Urban": "#FFB347",      "Soil":  "#C8A96E",
                    "Snow/Ice": "#B0E0FF",   "Fire":  "#FF6B6B",
                    "Drought": "#FFD166",    "Thermal": "#F4A261",
                    "Custom": "#D4A1FF",
                }
                col = tag_colors.get(cur_cat, "#8B949E")
                tk.Label(self.idx_inner,
                         text=f"  ── {cur_cat} ──",
                         bg=C["PANEL"], fg=col,
                         font=("Consolas", 8)).pack(anchor="w", pady=(6,2), padx=6)

            needed    = set(defn["bands"])
            supported = needed.issubset(avail)

            var = tk.BooleanVar(value=False)
            self.selected_indices[name] = var

            row = tk.Frame(self.idx_inner, bg=C["PANEL"])
            row.pack(fill="x", padx=4, pady=1)

            cb = ttk.Checkbutton(row, text=name, variable=var,
                                  state="normal" if supported else "disabled")
            cb.pack(side="left", padx=4)

            tk.Label(row, text=defn.get("formula_display", "")[:40],
                     bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas", 8)).pack(side="left", padx=6)

            if not supported:
                miss = needed - avail
                tk.Label(row, text=f"[缺: {', '.join(miss)}]",
                         bg=C["PANEL"], fg="#FF6B6B",
                         font=("Consolas", 8)).pack(side="right", padx=6)

            count += 1

            def on_enter(e, n=name, d=defn):
                self.info_bar.configure(
                    text=f"【{d.get('full_name', n)}】\n"
                         f"公式: {d.get('formula_display','')}\n"
                         f"值域: {d.get('range','—')}   波段: {', '.join(d['bands'])}\n"
                         f"{d.get('description','')}"
                )
            row.bind("<Enter>", on_enter)
            for child in row.winfo_children():
                child.bind("<Enter>", on_enter)

        self.count_label.configure(text=f"共 {count} 个指数")

    def _on_sensor_change(self, event=None):
        self._refresh_index_list()
        self._refresh_band_config()

    def _select_all(self):
        for var in self.selected_indices.values(): var.set(True)

    def _deselect_all(self):
        for var in self.selected_indices.values(): var.set(False)

    # ── 文件操作 ──────────────────────────────────────
    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="选择遥感影像",
            filetypes=[
                ("所有支持格式", "*.tif *.tiff *.img *.dat *.hdr *.nc"),
                ("GeoTIFF",      "*.tif *.tiff"),
                ("ENVI",         "*.img *.dat *.hdr"),
                ("NetCDF",       "*.nc"),
                ("所有文件",     "*.*"),
            ]
        )
        new_files = [f for f in files if f not in self.input_files]
        if not new_files:
            return

        # 对每个新文件：读取波段信息 → 弹窗确认/调整
        for fpath in new_files:
            # .hdr 文件重定向到对应的 .img/.dat
            p = Path(fpath)
            if p.suffix.lower() == ".hdr":
                for ext in [".img", ".dat", ".bil", ".bsq", ".bip"]:
                    candidate = p.with_suffix(ext)
                    if candidate.exists():
                        fpath = str(candidate)
                        break

            if not RASTERIO_AVAILABLE:
                self.input_files.append(fpath)
                self.file_list.insert(tk.END, f"  {Path(fpath).name}")
                continue

            # 读取文件元数据，弹出波段信息窗口
            try:
                band_info = self._read_band_info(fpath)
                confirmed = self._show_band_dialog(fpath, band_info)
                if confirmed:
                    self.input_files.append(fpath)
                    self.file_list.insert(tk.END, f"  {Path(fpath).name}")
            except Exception as e:
                # 读取失败也允许添加，计算时再报错
                ans = messagebox.askyesno(
                    "读取警告",
                    f"无法读取文件元数据：\n{Path(fpath).name}\n\n错误：{e}\n\n是否仍然添加该文件？"
                )
                if ans:
                    self.input_files.append(fpath)
                    self.file_list.insert(tk.END, f"  {Path(fpath).name}")

    def _read_band_info(self, fpath):
        """读取文件的波段信息，返回列表"""
        info = []
        with rasterio.open(fpath) as src:
            meta = src.meta
            for i in range(1, src.count + 1):
                band_tags  = src.tags(i)
                # 尝试从 tags 里拿波段名/波长（ENVI格式常有）
                bname = (band_tags.get("band_name")
                         or band_tags.get("BAND_NAME")
                         or band_tags.get("wavelength")
                         or src.descriptions[i-1]
                         or f"Band {i}")
                # 统计信息（只读一小块，节省时间）
                window = rasterio.windows.Window(0, 0,
                    min(256, src.width), min(256, src.height))
                sample = src.read(i, window=window).astype(float)
                sample = sample[sample != (src.nodata or 0)]
                stats = {}
                if sample.size > 0:
                    stats = {
                        "min":  float(np.nanmin(sample)),
                        "max":  float(np.nanmax(sample)),
                        "mean": float(np.nanmean(sample)),
                    }
                info.append({
                    "index":  i,
                    "name":   bname,
                    "dtype":  src.dtypes[i-1],
                    "stats":  stats,
                })
        return {"bands": info, "meta": meta, "path": fpath}

    def _show_band_dialog(self, fpath, band_info):
        """弹出波段信息对话框，返回 True=确认添加，False=取消"""
        C  = self.C
        dlg = tk.Toplevel(self.root)
        dlg.title(f"波段信息 — {Path(fpath).name}")
        dlg.configure(bg=C["BG"])
        dlg.resizable(True, True)
        dlg.grab_set()

        meta   = band_info["meta"]
        bands  = band_info["bands"]
        result = {"ok": False}

        # ── 文件概要 ──
        summary = tk.Frame(dlg, bg=C["PANEL"],
                           highlightbackground=C["BORDER"], highlightthickness=1)
        summary.pack(fill="x", padx=14, pady=(14, 6))

        w, h = meta.get("width", "?"), meta.get("height", "?")
        crs  = str(meta.get("crs", "未知"))[:60]
        driver = meta.get("driver", "?")
        nb   = meta.get("count", "?")

        for label, val in [
            ("文件名",   Path(fpath).name),
            ("格式",     driver),
            ("尺寸",     f"{w} × {h} 像素"),
            ("波段数",   f"{nb} 个波段"),
            ("坐标系",   crs),
        ]:
            row = tk.Frame(summary, bg=C["PANEL"])
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=f"{label}:", bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas", 9), width=8, anchor="e").pack(side="left", padx=(0, 6))
            tk.Label(row, text=val, bg=C["PANEL"], fg=C["TEXT"],
                     font=("Consolas", 9), anchor="w").pack(side="left")

        tk.Frame(summary, bg=C["PANEL"], height=6).pack()

        # ── 波段列表 ──
        tk.Label(dlg, text="  各波段信息（可参考以下内容在「波段映射」标签页调整编号）",
                 bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas", 9)).pack(anchor="w", padx=14, pady=(6, 2))

        tree_frame = tk.Frame(dlg, bg=C["PANEL"],
                              highlightbackground=C["BORDER"], highlightthickness=1)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        cols = ("idx", "name", "dtype", "min", "max", "mean")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                            height=min(len(bands), 12))
        headers = {"idx":"编号", "name":"波段名/描述", "dtype":"数据类型",
                   "min":"采样最小值", "max":"采样最大值", "mean":"采样均值"}
        widths  = {"idx":50, "name":180, "dtype":80, "min":100, "max":100, "mean":100}
        for c in cols:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c], anchor="center")

        for b in bands:
            s = b["stats"]
            tree.insert("", "end", values=(
                b["index"],
                b["name"],
                b["dtype"],
                f"{s.get('min', '—'):.4g}" if s else "—",
                f"{s.get('max', '—'):.4g}" if s else "—",
                f"{s.get('mean','—'):.4g}" if s else "—",
            ))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        # ── 提示 ──
        tk.Label(dlg,
                 text="  ✦ 采样统计基于左上角 256×256 像素，仅供参考",
                 bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas", 8)).pack(anchor="w", padx=14, pady=(0, 4))

        # ── 按钮 ──
        btn_row = tk.Frame(dlg, bg=C["BG"])
        btn_row.pack(fill="x", padx=14, pady=(0, 14))

        def on_ok():
            result["ok"] = True
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        ttk.Button(btn_row, text="✓ 添加文件", style="Accent.TButton",
                   command=on_ok).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="取消", command=on_cancel).pack(side="right")

        # 居中显示
        dlg.update_idletasks()
        pw = self.root.winfo_x() + self.root.winfo_width()  // 2
        ph = self.root.winfo_y() + self.root.winfo_height() // 2
        dw, dh = 640, 420
        dlg.geometry(f"{dw}x{dh}+{pw - dw//2}+{ph - dh//2}")

        self.root.wait_window(dlg)
        return result["ok"]

    def _clear_files(self):
        self.input_files.clear()
        self.file_list.delete(0, tk.END)

    def _smart_import(self):
        """智能导入：识别 Landsat / Sentinel-2 原始数据，自动完成波段映射"""
        if not SMART_IMPORT_AVAILABLE:
            messagebox.showerror("模块缺失",
                "smart_importer.py 未找到。\n"
                "请将 smart_importer.py 放在与 rs_calculator.py 同一目录下。")
            return

        dlg    = SmartImportDialog(self.root, self.C)
        result = dlg.wait()
        if not result:
            return

        sensor     = result.get("sensor", "")
        band_files = result.get("bands", {})
        scene_id   = result.get("scene_id", "scene")
        scale      = result.get("scale_factor", 1.0)
        offset     = result.get("offset", 0.0)
        run_now    = result.get("run_now", False)

        # ── 1. 切换传感器 ──
        try:
            self.selected_sensor.set(sensor)
            self._on_sensor_change()
        except Exception:
            pass

        # ── 2. 缩放参数 ──
        self.scale_factor.set(str(scale))
        self._smart_offset     = float(offset)
        self._smart_band_files = band_files
        self._smart_scene_id   = scene_id

        # ── 3. 清空文件列表，只显示场景名（不再列出每个波段文件）──
        self.input_files.clear()
        self.file_list.delete(0, tk.END)
        # 用场景 ID 作为一个虚拟条目，方便用户识别
        self.input_files.append("__SMART__")
        self.file_list.insert(tk.END, f"  ⚡ {scene_id}  [{len(band_files)} 个波段]")

        # ── 4. 更新输出路径为数据所在目录（如果用户没选过）──
        if not self.output_dir.get():
            self.output_dir.set(result.get("folder",""))

        # ── 5. 波段映射页编号设为 1 ──
        for bname in band_files:
            if bname in self.band_vars:
                self.band_vars[bname].set("1")

        # ── 6. 如果用户点了"导入并立即计算"──
        if run_now:
            chosen = [n for n, v in self.selected_indices.items() if v.get()]
            if not chosen:
                messagebox.showwarning("提示",
                    "导入成功！\n\n请先在左侧勾选要计算的指数，然后点击「开始计算」。")
                return
            if not self.output_dir.get():
                messagebox.showwarning("提示", "请先选择输出路径！")
                return
            if not RASTERIO_AVAILABLE:
                messagebox.showerror("依赖缺失", "请运行: pip install rasterio numpy")
                return
            threading.Thread(target=self._calc_thread,
                             args=(chosen,), daemon=True).start()

    def _browse_output(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d: self.output_dir.set(d)

    # ── 日志 ─────────────────────────────────────────
    def _log(self, msg, tag="info"):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    # ── 计算 ─────────────────────────────────────────
    def _run_calculation(self):
        chosen = [n for n, v in self.selected_indices.items() if v.get()]
        if not chosen:
            messagebox.showwarning("提示", "请选择至少一个指数！"); return
        if not self.input_files:
            messagebox.showwarning("提示", "请添加输入文件！"); return
        if not self.output_dir.get():
            messagebox.showwarning("提示", "请选择输出路径！"); return
        if not RASTERIO_AVAILABLE:
            messagebox.showerror("依赖缺失", "请运行: pip install rasterio numpy"); return
        threading.Thread(target=self._calc_thread, args=(chosen,), daemon=True).start()

    def _calc_thread(self, chosen_indices):
        self._set_status("计算中...", True)
        self._log("═"*55, "header")
        self._log("  RS Index Calculator v2.0 — 开始处理", "header")
        self._log("═"*55, "header")
        self._log(f"文件数: {len(self.input_files)}  |  指数: {', '.join(chosen_indices)}\n", "info")

        # 合并内置+自定义
        all_defs = dict(INDEX_DEFINITIONS)
        for k, v in self.custom_indices.items():
            formula_str = v["formula_display"]
            all_defs[k] = {**v, "func": lambda b, fs=formula_str: eval_custom_formula(fs, b)}

        # ═══════════════════════════════════════════════
        #  智能导入模式 vs 普通模式 分支
        # ═══════════════════════════════════════════════
        if self._smart_band_files:
            # ── 智能模式：所有波段来自独立文件，只运行一次 ──
            self._log(f"▶ 智能导入场景: {self._smart_scene_id}", "info")
            self._log(f"  共 {len(self._smart_band_files)} 个波段文件", "info")

            scale  = float(self.scale_factor.get())
            nodata = float(self.nodata_val.get())
            offset = self._smart_offset

            # 读取所有逻辑波段
            band_data = {}
            ref_profile = None
            for bname, bpath in self._smart_band_files.items():
                try:
                    with rasterio.open(bpath) as bsrc:
                        if ref_profile is None:
                            ref_profile = bsrc.profile.copy()
                        arr = bsrc.read(1).astype(np.float32)
                        src_nd = bsrc.nodata
                        if src_nd is not None:
                            arr = np.where(arr == src_nd, np.nan, arr)
                        arr = np.where(arr == nodata, np.nan, arr)
                        if scale != 1.0:
                            arr = arr * scale
                        if offset != 0.0:
                            arr = np.where(np.isnan(arr), np.nan, arr + offset)
                        band_data[bname] = arr
                        self._log(f"  ✓ 读取 {bname}: {Path(bpath).name}", "info")
                except Exception as be:
                    self._log(f"  ⚠ 读取 {bname} 失败: {be}", "warning")

            if not ref_profile:
                self._log("✗ 无法读取任何波段文件", "error")
                self._set_status("失败", False)
                return

            total = len(chosen_indices)
            done  = 0
            last_result = None
            last_name   = ""

            for idx_name in chosen_indices:
                defn   = all_defs.get(idx_name)
                needed = defn["bands"] if defn else []
                if not all(b in band_data for b in needed):
                    miss = [b for b in needed if b not in band_data]
                    self._log(f"  ✗ {idx_name}: 缺失波段 {miss}", "warning")
                    done += 1; continue
                try:
                    result = defn["func"](band_data).astype(np.float32)
                    out_profile = ref_profile.copy()
                    fmt = self.output_format.get()
                    if "ENVI" in fmt:
                        driver = "ENVI"
                        ext    = ".img" if ".img" in fmt else ".dat"
                        out_profile.pop("compress", None)
                        out_profile.pop("tiled", None)
                        out_profile.pop("interleave", None)
                    else:
                        driver, ext = "GTiff", ".tif"
                    out_profile.update(dtype=rasterio.float32, count=1,
                                       nodata=float("nan"), driver=driver)
                    out_name = f"{self._smart_scene_id}_{idx_name}{ext}"
                    out_path = os.path.join(self.output_dir.get(), out_name)
                    with rasterio.open(out_path, "w", **out_profile) as dst:
                        dst.write(result, 1)
                    self._log(f"  ✓ {idx_name} → {out_name}", "success")
                    last_result = result
                    last_name   = out_name
                except Exception as e:
                    self._log(f"  ✗ {idx_name}: {e}", "error")
                done += 1
                self.root.after(0, lambda d=done, t=total:
                    self.progress.configure(value=int(d/t*100) if t else 0))

            self._log("\n✓ 全部完成！", "success")
            self._set_status("完成", False)
            if last_result is not None and MATPLOTLIB_AVAILABLE:
                self.preview_result = last_result
                self.preview_name   = last_name
                self.root.after(200, self._refresh_preview)
            return   # 智能模式直接返回，不走下面的普通模式循环

        # ═══════════════════════════════════════════════
        #  普通模式：循环处理 input_files
        # ═══════════════════════════════════════════════
        total = len(self.input_files) * len(chosen_indices)
        done  = 0
        last_result = None
        last_name   = ""

        for fpath in self.input_files:
            fname = Path(fpath).stem
            p     = Path(fpath)
            self._log(f"▶ {p.name}", "info")
            try:
                actual_path = fpath
                if p.suffix.lower() == ".hdr":
                    for ext in [".img", ".dat", ".bil", ".bsq", ".bip"]:
                        candidate = p.with_suffix(ext)
                        if candidate.exists():
                            actual_path = str(candidate); break

                ap  = Path(actual_path)
                ext = ap.suffix.lower()
                fmt_map = {".tif":"GeoTIFF",".tiff":"GeoTIFF",".img":"ENVI",
                           ".dat":"ENVI",".bil":"ENVI(BIL)",".bsq":"ENVI(BSQ)",
                           ".bip":"ENVI(BIP)",".nc":"NetCDF"}
                self._log(f"  格式: {fmt_map.get(ext,f'未知({ext})')}  {ap.name}", "info")

                with rasterio.open(actual_path) as src:
                    profile = src.profile.copy()
                    n_bands = src.count
                    scale   = float(self.scale_factor.get())
                    nodata  = float(self.nodata_val.get())
                    self._log(
                        f"  尺寸: {src.width}×{src.height}  波段数: {n_bands}"
                        f"  类型: {src.dtypes[0]}"
                        + (f"  CRS: {src.crs.to_string()[:30]}" if src.crs else ""),
                        "info")

                    hdr_path = ap.with_suffix(".hdr")
                    if ext in (".img",".dat",".bil",".bsq",".bip") and hdr_path.exists():
                        hdr_bands = _parse_envi_hdr_band_names(str(hdr_path))
                        if hdr_bands:
                            self._log(f"  .hdr 波段名: {', '.join(hdr_bands[:8])}"
                                      + ("..." if len(hdr_bands)>8 else ""), "info")

                    band_data = {}
                    for bname, var in self.band_vars.items():
                        try:
                            bidx = int(var.get())
                            if 1 <= bidx <= n_bands:
                                arr = src.read(bidx).astype(np.float32)
                                src_nodata = src.nodata
                                if src_nodata is not None:
                                    arr = np.where(arr == src_nodata, np.nan, arr)
                                arr = np.where(arr == nodata, np.nan, arr)
                                if scale != 1.0:
                                    arr = arr * scale
                                band_data[bname] = arr
                        except ValueError:
                            pass

                    for idx_name in chosen_indices:
                        defn   = all_defs.get(idx_name)
                        needed = defn["bands"] if defn else []
                        if not all(b in band_data for b in needed):
                            self._log(f"  ✗ {idx_name}: 缺失波段 {needed}", "warning")
                            done += 1; continue
                        try:
                            result = defn["func"](band_data).astype(np.float32)
                            out_profile = profile.copy()

                            # 根据输出格式设置 driver 和后缀
                            fmt = self.output_format.get()
                            if fmt == "ENVI (.img + .hdr)":
                                driver, ext = "ENVI", ".img"
                            elif fmt == "ENVI (.dat + .hdr)":
                                driver, ext = "ENVI", ".dat"
                            else:
                                driver, ext = "GTiff", ".tif"

                            out_profile.update(
                                dtype=rasterio.float32, count=1,
                                nodata=float("nan"), driver=driver
                            )
                            # ENVI 不支持压缩参数，需移除
                            if driver == "ENVI":
                                out_profile.pop("compress", None)
                                out_profile.pop("tiled", None)
                                out_profile.pop("interleave", None)

                            out_name = f"{fname}_{idx_name}{ext}"
                            out_path = os.path.join(self.output_dir.get(), out_name)
                            with rasterio.open(out_path, "w", **out_profile) as dst:
                                dst.write(result, 1)
                            self._log(f"  ✓ {idx_name} → {out_name}", "success")
                            last_result = result
                            last_name   = out_name
                        except Exception as e:
                            self._log(f"  ✗ {idx_name}: {e}", "error")
                        done += 1
                        self.root.after(0, lambda d=done, t=total:
                            self.progress.configure(value=int(d/t*100) if t else 0))
            except Exception as e:
                self._log(f"  ✗ 无法读取: {e}", "error")

        self._log("\n✓ 全部完成！", "success")
        self._set_status("完成", False)

        # 自动跳转到预览
        if last_result is not None and MATPLOTLIB_AVAILABLE:
            self.preview_result = last_result
            self.preview_name   = last_name
            self.root.after(200, self._refresh_preview)

    def _set_status(self, msg, running):
        C = self.C
        self.root.after(0, lambda: (
            self.status_label.configure(text=msg, fg=C["ACCENT"] if running else C["MUTED"]),
            self.progress.configure(value=0) if not running else None
        ))


def main():
    root = tk.Tk()
    app = RSCalculatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

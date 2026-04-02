"""
data_sources.py
遥感数据来源导航面板
作为独立模块集成进 rs_calculator.py 的 Tab
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

# ══════════════════════════════════════════════════════
#  数据源定义
# ══════════════════════════════════════════════════════

DATA_SOURCES = [

    # ── 中国平台 ──────────────────────────────────────
    {
        "region": "中国",
        "name":   "地理空间数据云",
        "abbr":   "GSCloud",
        "url":    "https://www.gscloud.cn",
        "desc":   "国内最常用的遥感数据下载平台",
        "data": [
            "Landsat 5/7/8/9 全系列（L1/L2，免费）",
            "Sentinel-1/2 哨兵系列",
            "MODIS 全产品（MOD09/MOD13/MOD11 等）",
            "DEM 数字高程（SRTM 30m / ASTER GDEM 30m）",
            "中国气象卫星 FY 风云系列",
        ],
        "note": "注册即可下载，国内访问速度快，推荐优先使用",
        "color": "#00D4A1",
    },
    {
        "region": "中国",
        "name":   "国家地理信息公共服务平台（天地图）",
        "abbr":   "天地图",
        "url":    "https://www.tianditu.gov.cn",
        "desc":   "国家基础地理信息数据官方平台",
        "data": [
            "高分辨率底图（矢量/影像/地形）",
            "全国基础地理数据（省市县边界等）",
            "提供 API 接口供 GIS 开发调用",
        ],
        "note": "主要用于底图和行政边界，不直接提供多光谱遥感数据下载",
        "color": "#00D4A1",
    },
    {
        "region": "中国",
        "name":   "高分对地观测系统数据服务",
        "abbr":   "高分中心",
        "url":    "https://data.cresda.cn",
        "desc":   "中国高分卫星数据官方共享平台",
        "data": [
            "GF-1（2m 全色 / 8m 多光谱）",
            "GF-2（1m 全色 / 4m 多光谱）",
            "GF-3（SAR 雷达，1m）",
            "GF-4（静止轨道，50m）",
            "GF-5/6/7 全系列",
        ],
        "note": "部分数据需申请，科研用途一般可免费获取",
        "color": "#00D4A1",
    },
    {
        "region": "中国",
        "name":   "资源三号卫星数据服务",
        "abbr":   "ZY-3",
        "url":    "https://sasclouds.com/chinese/home",
        "desc":   "自然资源卫星遥感云服务平台",
        "data": [
            "资源三号（ZY-3）立体测图，2.1m",
            "资源一号（ZY-1）02D/02E，多光谱",
            "吉林一号系列商业卫星",
        ],
        "note": "侧重国土测绘和立体测量应用",
        "color": "#00D4A1",
    },

    # ── 国际平台 ──────────────────────────────────────
    {
        "region": "国际",
        "name":   "USGS EarthExplorer",
        "abbr":   "USGS",
        "url":    "https://earthexplorer.usgs.gov",
        "desc":   "美国地质调查局，Landsat 官方数据源",
        "data": [
            "Landsat 1–9 全历史档案（1972 年至今）",
            "Landsat Collection 2 L1/L2 地表反射率产品",
            "SRTM DEM 30m/90m",
            "ASTER 多光谱 / 热红外",
            "Sentinel-2（通过联合协议提供）",
            "MODIS 部分产品",
        ],
        "note": "Landsat 数据最权威来源，需注册，免费下载",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "NASA Earthdata",
        "abbr":   "NASA",
        "url":    "https://www.earthdata.nasa.gov",
        "desc":   "NASA 地球科学数据统一入口",
        "data": [
            "MODIS 全产品（MOD/MYD 系列，Terra/Aqua）",
            "VIIRS 中分辨率数据",
            "SMAP 土壤水分",
            "ICESat-2 激光雷达高程",
            "GEDI 全球植被高度（L2A/L2B）",
            "GPM 全球降水",
            "MERRA-2 大气再分析",
        ],
        "note": "MODIS 和 GEDI 数据首选，部分产品需通过 Earthdata Search 下载",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "NASA Earthdata Search",
        "abbr":   "Earthdata Search",
        "url":    "https://search.earthdata.nasa.gov",
        "desc":   "NASA 数据搜索与批量下载工具",
        "data": [
            "MODIS 地表反射率 MOD09GA/A1",
            "MODIS 植被指数 MOD13Q1（250m，16天合成）",
            "MODIS 地表温度 MOD11A1/A2",
            "GEDI 激光雷达植被结构",
            "ICESat-2 高程数据",
        ],
        "note": "支持空间范围、时间范围过滤，支持批量下载脚本生成",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "ESA Copernicus Data Space",
        "abbr":   "ESA / Copernicus",
        "url":    "https://dataspace.copernicus.eu",
        "desc":   "欧空局哨兵卫星官方数据门户（2023年新平台）",
        "data": [
            "Sentinel-1（SAR，C 波段，10m）",
            "Sentinel-2（MSI，10m/20m/60m，L1C/L2A）",
            "Sentinel-3（海洋/陆地/大气，300m）",
            "Sentinel-5P（大气成分，TROPOMI）",
            "Sentinel-6（海平面高度）",
        ],
        "note": "2023 年取代旧版 SciHub，现为 Sentinel 数据官方下载入口，免费",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "NOAA CLASS",
        "abbr":   "NOAA",
        "url":    "https://www.avl.class.noaa.gov",
        "desc":   "美国国家海洋大气局数据归档系统",
        "data": [
            "AVHRR（长时序植被监测，1981 年至今）",
            "VIIRS 陆地/海洋产品",
            "GOES 系列气象卫星",
            "JPSS 联合极轨卫星系统",
            "海表温度（SST）长时序产品",
        ],
        "note": "适合需要长时序气象和海洋遥感数据的研究",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "Alaska Satellite Facility (ASF)",
        "abbr":   "ASF",
        "url":    "https://asf.alaska.edu",
        "desc":   "全球最大的 SAR 雷达数据归档平台",
        "data": [
            "Sentinel-1 SAR（全球覆盖，免费）",
            "ALOS PALSAR / PALSAR-2（L 波段 SAR）",
            "ERS-1/2（历史 SAR 档案）",
            "RADARSAT-1",
            "InSAR 干涉差分数据（地形/形变）",
        ],
        "note": "SAR 数据首选平台，提供 Vertex 在线检索工具",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "OpenTopography",
        "abbr":   "OpenTopo",
        "url":    "https://opentopography.org",
        "desc":   "全球高分辨率地形数据共享平台",
        "data": [
            "SRTM 30m / 90m 全球 DEM",
            "ASTER GDEM v3（30m）",
            "ALOS World 3D（30m，精度更高）",
            "Copernicus DEM（30m/90m，欧洲精品）",
            "机载 LiDAR 点云（部分区域）",
        ],
        "note": "DEM 数据首选，下载简便，无需繁琐注册",
        "color": "#4FC3F7",
    },
    {
        "region": "国际",
        "name":   "Copernicus Global Land Service",
        "abbr":   "CGLS",
        "url":    "https://land.copernicus.eu/global",
        "desc":   "欧盟全球陆地产品服务平台",
        "data": [
            "全球 NDVI / LAI / FAPAR 产品（300m，10天）",
            "全球地表温度（LST）",
            "全球烧毁面积（BA300）",
            "全球积雪覆盖（FSC）",
            "土地利用/覆盖（LCCS 分类）",
        ],
        "note": "提供已制作好的全球生物物理参数产品，适合直接用于分析",
        "color": "#4FC3F7",
    },
]

REGIONS = ["全部", "中国", "国际"]


# ══════════════════════════════════════════════════════
#  构建数据源 Tab
# ══════════════════════════════════════════════════════

def build_data_source_tab(parent_frame, colors):
    """
    在给定的 Frame 里构建数据来源导航界面。
    """
    C = colors

    # ── 顶部说明栏 ──────────────────────────────────
    header = tk.Frame(parent_frame, bg=C["PANEL"],
                      highlightbackground=C["BORDER"], highlightthickness=1)
    header.pack(fill="x", padx=14, pady=(12, 6))

    tk.Label(header,
             text="  ◈ 遥感数据来源导航",
             bg=C["PANEL"], fg=C["ACCENT"],
             font=("Consolas", 11, "bold")).pack(side="left", padx=4, pady=8)
    tk.Label(header,
             text="点击网址直接在浏览器中打开 · 仅提供入口，不提供下载服务",
             bg=C["PANEL"], fg=C["MUTED"],
             font=("Consolas", 9)).pack(side="left", padx=8)

    # ── 筛选行 ──────────────────────────────────────
    filter_row = tk.Frame(parent_frame, bg=C["BG"])
    filter_row.pack(fill="x", padx=14, pady=(0, 4))

    tk.Label(filter_row, text="筛选:", bg=C["BG"], fg=C["MUTED"],
             font=("Consolas", 9)).pack(side="left")

    region_var = tk.StringVar(value="全部")
    search_var = tk.StringVar()

    for region in REGIONS:
        rb = ttk.Radiobutton(filter_row, text=region, variable=region_var,
                             value=region)
        rb.pack(side="left", padx=(8, 0))

    tk.Label(filter_row, text="  搜索:", bg=C["BG"], fg=C["MUTED"],
             font=("Consolas", 9)).pack(side="left", padx=(16, 0))
    search_entry = ttk.Entry(filter_row, textvariable=search_var, width=20)
    search_entry.pack(side="left", padx=4)

    # ── 卡片滚动区域 ────────────────────────────────
    outer = tk.Frame(parent_frame, bg=C["BG"])
    outer.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    canvas = tk.Canvas(outer, bg=C["BG"], borderwidth=0, highlightthickness=0)
    vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    cards_frame = tk.Frame(canvas, bg=C["BG"])

    cards_frame.bind("<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=cards_frame, anchor="nw")
    canvas.configure(yscrollcommand=vscroll.set)

    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # 鼠标滚轮支持
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # ── 构建/刷新卡片 ────────────────────────────────
    def refresh_cards(*_):
        for w in cards_frame.winfo_children():
            w.destroy()

        region_filter = region_var.get()
        search_kw     = search_var.get().strip().lower()

        # 按 region 分组显示
        current_region = None

        for source in DATA_SOURCES:
            # 筛选
            if region_filter != "全部" and source["region"] != region_filter:
                continue
            if search_kw:
                haystack = (source["name"] + source["desc"] +
                            " ".join(source["data"])).lower()
                if search_kw not in haystack:
                    continue

            # Region 分组标题
            if source["region"] != current_region:
                current_region = source["region"]
                region_label = "🇨🇳  中国平台" if current_region == "中国" else "🌐  国际平台"
                sep = tk.Frame(cards_frame, bg=C["BG"])
                sep.pack(fill="x", pady=(10, 2))
                tk.Frame(sep, bg=C["BORDER"], height=1).pack(fill="x", side="left",
                    expand=True, pady=8)
                tk.Label(sep, text=f"  {region_label}  ",
                         bg=C["BG"], fg=source["color"],
                         font=("Consolas", 9, "bold")).pack(side="left")
                tk.Frame(sep, bg=C["BORDER"], height=1).pack(fill="x", side="left",
                    expand=True, pady=8)

            # 卡片
            _build_card(cards_frame, source, C)

        # 无结果提示
        if not cards_frame.winfo_children():
            tk.Label(cards_frame, text="没有匹配的数据源",
                     bg=C["BG"], fg=C["MUTED"],
                     font=("Consolas", 10)).pack(pady=30)

        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    region_var.trace_add("write", refresh_cards)
    search_var.trace_add("write", refresh_cards)

    refresh_cards()


def _build_card(parent, source, C):
    """构建单个数据源卡片"""
    accent = source["color"]

    card = tk.Frame(parent, bg=C["PANEL"], bd=0,
                    highlightbackground=accent,
                    highlightthickness=1)
    card.pack(fill="x", pady=4)

    # ── 左色条 ──
    bar = tk.Frame(card, bg=accent, width=4)
    bar.pack(side="left", fill="y")

    # ── 内容区 ──
    body = tk.Frame(card, bg=C["PANEL"])
    body.pack(side="left", fill="both", expand=True, padx=10, pady=8)

    # 名称行
    name_row = tk.Frame(body, bg=C["PANEL"])
    name_row.pack(fill="x")

    tk.Label(name_row,
             text=source["name"],
             bg=C["PANEL"], fg=C["TEXT"],
             font=("Consolas", 10, "bold")).pack(side="left")

    tk.Label(name_row,
             text=f"  [{source['abbr']}]",
             bg=C["PANEL"], fg=accent,
             font=("Consolas", 9)).pack(side="left")

    # 描述
    tk.Label(body,
             text=source["desc"],
             bg=C["PANEL"], fg=C["MUTED"],
             font=("Consolas", 9),
             anchor="w").pack(fill="x", pady=(1, 4))

    # 数据列表
    data_frame = tk.Frame(body, bg=C["PANEL"])
    data_frame.pack(fill="x")

    # 两列排列
    col1 = tk.Frame(data_frame, bg=C["PANEL"])
    col2 = tk.Frame(data_frame, bg=C["PANEL"])
    col1.pack(side="left", anchor="n", padx=(0, 20))
    col2.pack(side="left", anchor="n")

    items = source["data"]
    half  = (len(items) + 1) // 2
    for i, item in enumerate(items):
        target = col1 if i < half else col2
        row = tk.Frame(target, bg=C["PANEL"])
        row.pack(fill="x", pady=1)
        tk.Label(row, text="▸", bg=C["PANEL"], fg=accent,
                 font=("Consolas", 8)).pack(side="left")
        tk.Label(row, text=item, bg=C["PANEL"], fg=C["TEXT"],
                 font=("Consolas", 8), anchor="w").pack(side="left", padx=3)

    # 备注
    if source.get("note"):
        tk.Label(body,
                 text=f"  ✦ {source['note']}",
                 bg=C["PANEL"], fg=C["MUTED"],
                 font=("Consolas", 8),
                 anchor="w").pack(fill="x", pady=(4, 0))

    # ── 右侧：打开按钮 ──
    right = tk.Frame(card, bg=C["PANEL"])
    right.pack(side="right", padx=12, pady=8)

    url = source["url"]

    url_label = tk.Label(right,
                         text=url.replace("https://", ""),
                         bg=C["PANEL"], fg=accent,
                         font=("Consolas", 8),
                         cursor="hand2")
    url_label.pack(anchor="e")
    url_label.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
    url_label.bind("<Enter>", lambda e: url_label.configure(fg="#FFFFFF"))
    url_label.bind("<Leave>", lambda e: url_label.configure(fg=accent))

    open_btn = tk.Button(right,
                         text="打开网站 →",
                         bg=accent, fg="#0D1117",
                         font=("Consolas", 9, "bold"),
                         relief="flat", bd=0,
                         padx=10, pady=4,
                         cursor="hand2",
                         activebackground="#00B88A",
                         activeforeground="#0D1117",
                         command=lambda u=url: webbrowser.open(u))
    open_btn.pack(anchor="e", pady=(4, 0))

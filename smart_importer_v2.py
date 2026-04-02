"""
smart_importer.py  v2
智能原始数据导入模块
支持：
  - Landsat 5/7/8/9  →  选 *_MTL.txt 或 *_MTL.json
  - Sentinel-2        →  选 .SAFE 文件夹
"""

import os, re, json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

S2_BAND_MAP = {
    "B01":"Coastal","B02":"Blue","B03":"Green","B04":"Red",
    "B05":"RedEdge1","B06":"RedEdge2","B07":"RedEdge3",
    "B08":"NIR","B8A":"NIR_N","B11":"SWIR1","B12":"SWIR2",
}
S2_RES_PRIORITY = {"10m":0,"20m":1,"60m":2}
LANDSAT_L2_C2_SCALE  = 2.75e-5
LANDSAT_L2_C2_OFFSET = -0.2

# ══ MTL 解析 ═══════════════════════════════════════════
def parse_mtl_txt(mtl_path):
    kv = {}
    with open(mtl_path,"r",encoding="utf-8",errors="ignore") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith(("GROUP","END")):
                k,_,v = line.partition("=")
                kv[k.strip()] = v.strip().strip('"')
    return kv

def parse_mtl_json(mtl_path):
    with open(mtl_path,"r",encoding="utf-8") as f:
        data = json.load(f)
    kv = {}
    def flatten(d):
        for k,v in d.items():
            if isinstance(v,dict): flatten(v)
            else: kv[k] = str(v)
    flatten(data)
    return kv

def build_landsat_result_from_kv(kv, mtl_path):
    mtl_dir    = Path(mtl_path).parent
    spacecraft = kv.get("SPACECRAFT_ID", kv.get("spacecraftId","")).strip().strip('"')
    proc_level = kv.get("PROCESSING_LEVEL", kv.get("processingLevel","")).strip().strip('"')
    collection = kv.get("COLLECTION_NUMBER", kv.get("collectionNumber","")).strip().strip('"')
    date_acq   = kv.get("DATE_ACQUIRED", kv.get("dateAcquired","")).strip().strip('"')
    scene_id   = kv.get("LANDSAT_PRODUCT_ID", kv.get("landsatProductId","")).strip().strip('"')
    if not scene_id:
        scene_id = Path(mtl_path).stem.replace("_MTL","")

    sc = spacecraft.upper().replace("_","").replace(" ","")
    if   "LANDSAT9" in sc or "LANDSAT8" in sc: sensor_name = "Landsat 8/9 (OLI)"
    elif "LANDSAT7" in sc:                      sensor_name = "Landsat 7 (ETM+)"
    else:                                       sensor_name = "Landsat 5 (TM)"

    is_l2 = "L2" in proc_level.upper()
    is_c2 = collection.strip() == "02"
    scale_factor = LANDSAT_L2_C2_SCALE  if (is_l2 and is_c2) else 1.0
    offset       = LANDSAT_L2_C2_OFFSET if (is_l2 and is_c2) else 0.0

    # 收集所有含 FILE_NAME 和 BAND 的键
    band_files_raw = {k.upper():v for k,v in kv.items()
                      if "FILE_NAME" in k.upper() and "BAND" in k.upper()}

    # 定义逻辑名 → MTL key 候选列表
    if sensor_name == "Landsat 8/9 (OLI)":
        if is_l2:
            logical_map = {
                "Coastal":["FILE_NAME_BAND_SR_B1"],
                "Blue":   ["FILE_NAME_BAND_SR_B2"],
                "Green":  ["FILE_NAME_BAND_SR_B3"],
                "Red":    ["FILE_NAME_BAND_SR_B4"],
                "NIR":    ["FILE_NAME_BAND_SR_B5"],
                "SWIR1":  ["FILE_NAME_BAND_SR_B6"],
                "SWIR2":  ["FILE_NAME_BAND_SR_B7"],
                "TIR1":   ["FILE_NAME_BAND_ST_B10"],
                "TIR2":   ["FILE_NAME_BAND_ST_B11"],
            }
        else:
            logical_map = {
                "Coastal":["FILE_NAME_BAND_1"],
                "Blue":   ["FILE_NAME_BAND_2"],
                "Green":  ["FILE_NAME_BAND_3"],
                "Red":    ["FILE_NAME_BAND_4"],
                "NIR":    ["FILE_NAME_BAND_5"],
                "SWIR1":  ["FILE_NAME_BAND_6"],
                "SWIR2":  ["FILE_NAME_BAND_7"],
                "TIR1":   ["FILE_NAME_BAND_10"],
                "TIR2":   ["FILE_NAME_BAND_11"],
            }
    elif sensor_name == "Landsat 7 (ETM+)":
        logical_map = {
            "Blue": ["FILE_NAME_BAND_SR_B1","FILE_NAME_BAND_1"],
            "Green":["FILE_NAME_BAND_SR_B2","FILE_NAME_BAND_2"],
            "Red":  ["FILE_NAME_BAND_SR_B3","FILE_NAME_BAND_3"],
            "NIR":  ["FILE_NAME_BAND_SR_B4","FILE_NAME_BAND_4"],
            "SWIR1":["FILE_NAME_BAND_SR_B5","FILE_NAME_BAND_5"],
            "TIR":  ["FILE_NAME_BAND_SR_B6","FILE_NAME_BAND_6_VCID_1","FILE_NAME_BAND_6"],
            "SWIR2":["FILE_NAME_BAND_SR_B7","FILE_NAME_BAND_7"],
        }
    else:
        logical_map = {
            "Blue": ["FILE_NAME_BAND_SR_B1","FILE_NAME_BAND_1"],
            "Green":["FILE_NAME_BAND_SR_B2","FILE_NAME_BAND_2"],
            "Red":  ["FILE_NAME_BAND_SR_B3","FILE_NAME_BAND_3"],
            "NIR":  ["FILE_NAME_BAND_SR_B4","FILE_NAME_BAND_4"],
            "SWIR1":["FILE_NAME_BAND_SR_B5","FILE_NAME_BAND_5"],
            "TIR":  ["FILE_NAME_BAND_SR_B6","FILE_NAME_BAND_6"],
            "SWIR2":["FILE_NAME_BAND_SR_B7","FILE_NAME_BAND_7"],
        }

    found_bands, missing = {}, []
    # 建立文件名大写 → 实际路径的索引，避免大小写问题
    dir_index = {f.name.upper(): f for f in mtl_dir.iterdir() if f.is_file()}

    for logical_name, candidate_keys in logical_map.items():
        matched_file = None
        for ck in candidate_keys:
            val = band_files_raw.get(ck.upper())
            if val:
                real = dir_index.get(val.upper())
                if real:
                    matched_file = str(real)
                    break
        if matched_file:
            found_bands[logical_name] = matched_file
        else:
            missing.append(logical_name)

    return {
        "sensor":       sensor_name,
        "scene_id":     scene_id,
        "level":        proc_level,
        "collection":   f"C{collection}" if collection else "未知",
        "date":         date_acq,
        "scale_factor": scale_factor,
        "offset":       offset,
        "bands":        found_bands,
        "missing":      missing,
        "folder":       str(mtl_dir),
        "source":       "MTL",
    }

# ══ Sentinel-2 扫描 ════════════════════════════════════
def scan_sentinel2_safe(safe_folder, resolution="10m"):
    safe_folder = Path(safe_folder)
    name = safe_folder.name
    level = "L2A" if "MSIL2A" in name else "L1C"
    scene_id = name.replace(".SAFE","")

    all_jp2 = list(safe_folder.rglob("*.jp2"))
    res_groups = {}
    for jp2 in all_jp2:
        for res in ["10m","20m","60m"]:
            if f"R{res}" in str(jp2) or f"_{res}" in jp2.name:
                res_groups.setdefault(res,[]).append(jp2); break

    available_res = sorted(res_groups.keys(), key=lambda r: S2_RES_PRIORITY.get(r,99))
    target_res = resolution if resolution in res_groups else (available_res[0] if available_res else None)
    if not target_res: return None

    found_bands, missing = {}, []
    for band_key, logical_name in S2_BAND_MAP.items():
        matched = None
        for jp2 in res_groups.get(target_res,[]):
            if f"_{band_key}_" in jp2.name or jp2.name.endswith(f"_{band_key}.jp2"):
                matched = str(jp2); break
        if not matched:
            for fr in available_res:
                if fr == target_res: continue
                for jp2 in res_groups.get(fr,[]):
                    if f"_{band_key}_" in jp2.name or jp2.name.endswith(f"_{band_key}.jp2"):
                        matched = str(jp2); break
                if matched: break
        if matched: found_bands[logical_name] = matched
        else:       missing.append(logical_name)

    return {
        "sensor":"Sentinel-2 (MSI)", "scene_id":scene_id,
        "level":level, "collection":"—",
        "date": scene_id[11:19] if len(scene_id)>19 else "",
        "resolution":target_res, "available_res":available_res,
        "bands":found_bands, "missing":missing,
        "folder":str(safe_folder),
        "scale_factor":0.0001, "offset":0.0, "source":"SAFE",
    }

# ══ 弹窗 UI ════════════════════════════════════════════
class SmartImportDialog:
    def __init__(self, parent, colors):
        self.parent = parent
        self.C = colors
        self.result = None
        self._scan_result = None

        self.dlg = tk.Toplevel(parent)
        self.dlg.title("智能原始数据导入")
        self.dlg.configure(bg=colors["BG"])
        self.dlg.geometry("860x620")
        self.dlg.resizable(True, True)
        self.dlg.grab_set()
        self._build()

    def _build(self):
        C, dlg = self.C, self.dlg

        # 说明栏
        tip = tk.Frame(dlg, bg=C["PANEL"],
                       highlightbackground=C["BORDER"], highlightthickness=1)
        tip.pack(fill="x", padx=14, pady=(14,6))
        for sensor, desc in [
            ("Landsat 5/7/8/9", "选择产品文件夹内的 *_MTL.txt 或 *_MTL.json，自动读取全部波段"),
            ("Sentinel-2 (MSI)", "选择解压后的 *.SAFE 文件夹（含 GRANULE/IMG_DATA）"),
        ]:
            r = tk.Frame(tip, bg=C["PANEL"]); r.pack(fill="x", padx=10, pady=3)
            tk.Label(r, text=f"◈ {sensor}", bg=C["PANEL"], fg=C["ACCENT"],
                     font=("Consolas",9,"bold"), width=20, anchor="w").pack(side="left")
            tk.Label(r, text=desc, bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas",9), anchor="w").pack(side="left")
        tk.Frame(tip, bg=C["PANEL"], height=4).pack()

        # 按钮行
        btn_row = tk.Frame(dlg, bg=C["BG"])
        btn_row.pack(fill="x", padx=14, pady=6)
        ttk.Button(btn_row, text="📄  选择 Landsat MTL 文件",
                   command=self._pick_landsat_mtl).pack(side="left", padx=(0,10))
        ttk.Button(btn_row, text="📁  选择 Sentinel-2 .SAFE 文件夹",
                   command=self._pick_sentinel2).pack(side="left", padx=(0,20))
        tk.Label(btn_row, text="S2 分辨率:", bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas",9)).pack(side="left")
        self.s2_res = tk.StringVar(value="10m")
        ttk.Combobox(btn_row, textvariable=self.s2_res,
                     values=["10m","20m","60m"], state="readonly", width=6).pack(side="left", padx=(4,0))

        # 元信息面板（两列）
        tk.Label(dlg, text="  扫描结果", bg=C["BG"], fg=C["MUTED"],
                 font=("Consolas",9)).pack(anchor="w", padx=14, pady=(8,2))
        info_panel = tk.Frame(dlg, bg=C["PANEL"],
                              highlightbackground=C["BORDER"], highlightthickness=1)
        info_panel.pack(fill="x", padx=14, pady=(0,4))
        self.info_labels = {}
        meta_fields = [
            ("sensor","传感器"),("scene_id","场景ID"),("level","产品级别"),("collection","Collection"),
            ("date","获取日期"),("scale","缩放/偏移"),("found","识别波段"),("missing","缺失波段"),
        ]
        left_m  = tk.Frame(info_panel, bg=C["PANEL"])
        right_m = tk.Frame(info_panel, bg=C["PANEL"])
        left_m.pack(side="left",  fill="x", expand=True, padx=(10,0), pady=6)
        right_m.pack(side="left", fill="x", expand=True, padx=(0,10), pady=6)
        for i,(key,label) in enumerate(meta_fields):
            target = left_m if i < 4 else right_m
            row = tk.Frame(target, bg=C["PANEL"]); row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", bg=C["PANEL"], fg=C["MUTED"],
                     font=("Consolas",9), width=11, anchor="e").pack(side="left", padx=(0,6))
            lbl = tk.Label(row, text="—", bg=C["PANEL"], fg=C["TEXT"],
                           font=("Consolas",9), anchor="w")
            lbl.pack(side="left")
            self.info_labels[key] = lbl

        # 波段详情表
        tk.Label(dlg, text="  波段匹配详情（确认后无需再手动添加文件）",
                 bg=C["BG"], fg=C["MUTED"], font=("Consolas",9)).pack(anchor="w", padx=14, pady=(4,2))
        tree_frame = tk.Frame(dlg, bg=C["PANEL"],
                               highlightbackground=C["BORDER"], highlightthickness=1)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0,6))
        cols = ("logical","filename","status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=9)
        self.tree.heading("logical",  text="逻辑波段")
        self.tree.heading("filename", text="匹配文件名")
        self.tree.heading("status",   text="状态")
        self.tree.column("logical",  width=90,  anchor="center")
        self.tree.column("filename", width=580)
        self.tree.column("status",   width=70,  anchor="center")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # 底部按钮
        bottom = tk.Frame(dlg, bg=C["BG"])
        bottom.pack(fill="x", padx=14, pady=(0,14))
        ttk.Button(bottom, text="取消", command=dlg.destroy).pack(side="right", padx=(6,0))
        self.run_btn = ttk.Button(bottom, text="✓ 导入并立即计算",
                                   style="Accent.TButton",
                                   command=lambda: self._confirm(run_now=True),
                                   state="disabled")
        self.run_btn.pack(side="right", padx=(6,0))
        self.import_btn = ttk.Button(bottom, text="仅导入",
                                      command=lambda: self._confirm(run_now=False),
                                      state="disabled")
        self.import_btn.pack(side="right")

        # 居中
        dlg.update_idletasks()
        pw = self.parent.winfo_x() + self.parent.winfo_width()  // 2
        ph = self.parent.winfo_y() + self.parent.winfo_height() // 2
        dlg.geometry(f"860x620+{pw-430}+{ph-310}")

    def _pick_landsat_mtl(self):
        path = filedialog.askopenfilename(
            title="选择 Landsat MTL 文件",
            filetypes=[("MTL 元数据","*_MTL.txt *_MTL.json *.txt *.json"),("所有文件","*.*")])
        if not path: return
        try:
            kv = parse_mtl_json(path) if Path(path).suffix.lower()==".json" else parse_mtl_txt(path)
            result = build_landsat_result_from_kv(kv, path)
            if not result["bands"]:
                messagebox.showerror("解析失败",
                    "未匹配到波段文件。\n请确认 TIF 文件与 MTL 在同一文件夹。"); return
            self._show_result(result)
        except Exception as e:
            messagebox.showerror("解析出错", f"MTL 解析失败：\n{e}")

    def _pick_sentinel2(self):
        folder = filedialog.askdirectory(title="选择 Sentinel-2 .SAFE 文件夹")
        if not folder: return
        p = Path(folder)
        safe_root = p
        for candidate in [p, p.parent, p.parent.parent]:
            try:
                if "GRANULE" in [x.name for x in candidate.iterdir() if x.is_dir()]:
                    safe_root = candidate; break
            except Exception: pass
        result = scan_sentinel2_safe(safe_root, resolution=self.s2_res.get())
        if not result or not result["bands"]:
            messagebox.showerror("识别失败",
                "未找到 Sentinel-2 波段文件。\n请确认选择了含 GRANULE 的 .SAFE 文件夹。"); return
        self._show_result(result)

    def _show_result(self, result):
        self._scan_result = result
        C = self.C
        scale  = result.get("scale_factor", 1.0)
        offset = result.get("offset", 0.0)
        scale_str = f"{scale}" + (f"  /  偏移 {offset}" if offset else "")
        updates = {
            "sensor":     (result.get("sensor","—"),       C["ACCENT"]),
            "scene_id":   (result.get("scene_id","—")[:55],C["TEXT"]),
            "level":      (result.get("level","—"),         C["TEXT"]),
            "collection": (result.get("collection","—"),    C["TEXT"]),
            "date":       (result.get("date","—"),          C["TEXT"]),
            "scale":      (scale_str,                       C["TEXT"]),
            "found":      (f"{len(result['bands'])} 个",   C["ACCENT"]),
            "missing":    (
                ", ".join(result.get("missing",[])) or "无",
                "#FF6B6B" if result.get("missing") else C["ACCENT"]
            ),
        }
        for key,(text,color) in updates.items():
            self.info_labels[key].configure(text=text, fg=color)

        for item in self.tree.get_children(): self.tree.delete(item)
        for bname, fpath in result["bands"].items():
            self.tree.insert("","end", values=(bname, Path(fpath).name,"✓ 已匹配"), tags=("ok",))
        for bname in result.get("missing",[]):
            self.tree.insert("","end", values=(bname,"未找到","✗ 缺失"), tags=("miss",))
        self.tree.tag_configure("ok",   foreground=C["ACCENT"])
        self.tree.tag_configure("miss", foreground="#FF6B6B")

        self.import_btn.configure(state="normal")
        self.run_btn.configure(state="normal")

    def _confirm(self, run_now=False):
        if self._scan_result:
            self._scan_result["run_now"] = run_now
            self.result = self._scan_result
        self.dlg.destroy()

    def wait(self):
        self.parent.wait_window(self.dlg)
        return self.result

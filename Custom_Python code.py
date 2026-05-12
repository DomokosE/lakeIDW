# -*- coding: utf-8 -*-

import os
import math
import heapq
import numpy as np
import geopandas as gpd
import pandas as pd

from rasterio import features
from rasterio.transform import from_origin
import rasterio

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ============================================================
# SETTINGS
# ============================================================
konyvtar = "c:/IDW_Python/"
shapes_folder = konyvtar

output_folder_tif = os.path.join(konyvtar, "TIF_9am_post2")
output_folder_png = os.path.join(konyvtar, "Python_png_9am_post2")

os.makedirs(output_folder_tif, exist_ok=True)
os.makedirs(output_folder_png, exist_ok=True)

kikotok_shp = os.path.join(shapes_folder, "lake.shp")
meres_csv = os.path.join(shapes_folder, "9AM_POST2.csv")

cell_size = 0.00001
power = 2.0

# ============================================================
# VARIABLES
# ============================================================
valtozo_oszlopok = [
    "Temperature",
    "DO mg/l",
    "pH",
    "ORP mV",
    "Turbidity NTU",
    "EC µS/cm",
    "Salinity g/kg",
    "TDS ppm",
    "mg NO3-N/L",
    "TP mg/l",
    "mg OP-P/L",
    "mg NH4-N/L",
    "mg NO2-N/L",
]

# ============================================================
# GLOBAL SCALE
# ============================================================
SCALE = {
    "Temperature": (13, 27),
    "DO mg/l": (6, 16.5),
    "pH": (7.4, 9),
    "ORP mV": (140, 265),
    "Turbidity NTU": (0, 15.5),
    "EC µS/cm": (470, 650),
    "Salinity g/kg": (0.250, 0.345),
    "TDS ppm": (237, 324.1),
    "mg NO3-N/L": (0.5, 5.5),
    "TP mg/l": (0, 0.5),
    "mg OP-P/L": (0, 0.01),
    "mg NH4-N/L": (0, 0.55),
    "mg NO2-N/L": (0, 0.02),
}

# ============================================================
# FUNCTIONS
# ============================================================
def coord_to_index(x, y, minx, maxy, cell):
    col = int((x - minx) // cell)
    row = int((maxy - y) // cell)
    return row, col

def dijkstra_distance_map(sr, sc, water_mask, cell):
    h, w = water_mask.shape
    dist = np.full((h, w), np.inf)
    visited = np.zeros((h, w), dtype=bool)

    diag = cell * math.sqrt(2)
    neigh = [(-1,0,cell),(1,0,cell),(0,-1,cell),(0,1,cell),
             (-1,-1,diag),(-1,1,diag),(1,-1,diag),(1,1,diag)]

    dist[sr, sc] = 0
    heap = [(0, sr, sc)]

    while heap:
        d, r, c = heapq.heappop(heap)
        if visited[r, c]:
            continue
        visited[r, c] = True

        for dr, dc, cost in neigh:
            nr, nc = r+dr, c+dc
            if 0 <= nr < h and 0 <= nc < w and water_mask[nr, nc] == 1:
                nd = d + cost
                if nd < dist[nr, nc]:
                    dist[nr, nc] = nd
                    heapq.heappush(heap, (nd, nr, nc))
    return dist

def png_mentes_hamis_szin(arr, path, cmap, vmin, vmax):
    masked = np.ma.masked_invalid(arr)

    fig, ax = plt.subplots(figsize=(6,4))
    plt.subplots_adjust(top=0.80)
    im = ax.imshow(masked, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.axis('off')
    ax.set_title("Custom-Python", color='white', fontsize=12, fontweight='regular', y=1.55)

    cbar = plt.colorbar(im, ax=ax, fraction=0.08, pad=0.08, shrink=0.6, aspect=12)

    mid = (vmin + vmax) / 2
    cbar.set_ticks([vmin, mid, vmax])

    cbar.set_ticklabels([
        f"{vmin:.2f}",
        f"{mid:.2f}",
        f"{vmax:.2f}"
    ])

    cbar.ax.tick_params(labelsize=8, colors='white', length=0)
    cbar.outline.set_visible(False)
    
    plt.savefig(path, dpi=200, transparent=True)
    plt.close(fig)
            
    
# ============================================================
# COLORMAP
# ============================================================
szinskala = LinearSegmentedColormap.from_list(
    "kek_sarga_piros",
    [(0,0,0.35),(1,1,0),(1,0,0)], N=256
)

# ============================================================
# LOAD DATA
# ============================================================
ports = gpd.read_file(kikotok_shp)


ports["id_szam"] = pd.to_numeric(ports["id"]).astype(int)

adat = pd.read_csv(meres_csv)
adat.columns = [c.strip() for c in adat.columns]

adat["Port ID_szam"] = pd.to_numeric(adat["Port ID"]).astype(int)

points = gpd.GeoDataFrame(
    adat,
    geometry=gpd.points_from_xy(adat["Measure LOG"], adat["Measure LAT"]),
    crs="EPSG:4326"
).to_crs(ports.crs)

# ============================================================
# MAIN LOOP
# ============================================================
for pid in points["Port ID_szam"].unique():

    port_geom = ports[ports["id_szam"] == pid].geometry.union_all()

    minx, miny, maxx, maxy = gpd.GeoSeries([port_geom]).total_bounds
    width = int((maxx - minx) / cell_size)
    height = int((maxy - miny) / cell_size)

    transform = from_origin(minx, maxy, cell_size, cell_size)

    water_mask = features.rasterize(
        [(port_geom, 1)],
        out_shape=(height, width),
        transform=transform
    )

    for var in valtozo_oszlopok:

        dfp = points[points["Port ID_szam"] == pid].copy()
        dfp[var] = pd.to_numeric(dfp[var], errors="coerce")
        dfp = dfp.dropna(subset=[var])

        if dfp.empty:
            continue

        acc_val = np.zeros((height, width))
        acc_wgt = np.zeros((height, width))

        for _, r in dfp.iterrows():
            sr, sc = coord_to_index(r.geometry.x, r.geometry.y, minx, maxy, cell_size)

            if not (0 <= sr < height and 0 <= sc < width):
                continue

            dmap = dijkstra_distance_map(sr, sc, water_mask, cell_size)

            w = np.where(np.isfinite(dmap) & (dmap > 0), 1/(dmap**power), 0)
            w[sr, sc] = 1/(1e-6**power)

            acc_val += w * r[var]
            acc_wgt += w

        result = np.where(acc_wgt > 0, acc_val / acc_wgt, np.nan)
        result[water_mask == 0] = np.nan

        # SCALE
        if var in SCALE:
            vmin, vmax = SCALE[var]
        else:
            vmin = np.nanmin(result)
            vmax = np.nanmax(result)

        # SAVE TIF
        safe_var = var.replace("/", "_").replace(" ", "_")
        out_tif = os.path.join(output_folder_tif, f"{pid}_{safe_var}.tif")

        with rasterio.open(
            out_tif,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=ports.crs,
            transform=transform,
            nodata=np.nan
        ) as dst:
            dst.write(result.astype("float32"), 1)

        # SAVE PNG
        out_png = os.path.join(output_folder_png, f"{pid}_{safe_var}.png")
        png_mentes_hamis_szin(result, out_png, szinskala, vmin, vmax)

print("FINISHED ✔")

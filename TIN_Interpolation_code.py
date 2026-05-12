import processing
import os
from qgis.core import QgsVectorLayer

# ---------- INPUT ----------
shp_path = r"C:/TIN_method/TIN_9AMP2.shp"
output_folder = r"C:/TIN_method/interpolated_9am_post2"

os.makedirs(output_folder, exist_ok=True)

layer = QgsVectorLayer(shp_path, "points", "ogr")
fields = layer.fields()

# ---------- EXTENT ----------
extent = '17.956466094,17.968247304,47.115207240,47.122824713 [EPSG:4326]'

# ---------- LOOP ----------
for i in range(4,len(fields)):

    field_name = fields[i].name()

    # text багануудыг алгасна
    if fields[i].typeName().lower() in ['string', 'text']:
        continue

    safe_name = field_name.replace(" ", "_").replace("/", "_").replace("-", "_")

    print("Processing:", safe_name)

    processing.run("qgis:tininterpolation", {
        'INTERPOLATION_DATA': f'{shp_path}::~::0::~::{i}::~::0',
        'METHOD': 0,   # 0 = Linear, 1 = Clough-Tocher
        'EXTENT': extent,
        'PIXEL_SIZE': 0.00002,
        'OUTPUT': f'C:/TIN_method/interpolated_9am_post2/{safe_name}_TIN.tif'
    })

print("FINISHED ✔ бүх баганад TIN үүслээ")
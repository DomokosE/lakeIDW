import processing
import os
from qgis.core import QgsVectorLayer, QgsProject

# ================= SETTINGS =================

csv_path = r"C:/IDW_validation/4 points_8AM.csv"
output_folder = r"C:/IDW_validation/interpolation"

os.makedirs(output_folder, exist_ok=True)

uri = f"file:///{csv_path}?type=csv&detectTypes=yes&xField=Measure%20LOG&yField=Measure%20LAT&crs=EPSG:4326"

# ================= LOAD LAYER =================

layer = QgsVectorLayer(uri, "csv", "delimitedtext")

if not layer.isValid():
    raise Exception("❌ CSV layer load FAILED")

# 🔥 CRASH FIX (хамгийн чухал)
QgsProject.instance().addMapLayer(layer)

source = layer.source()
fields = layer.fields()

# ================= EXTENT =================

extent = '17.956027705,17.967637805,47.115501301,47.123771101 [EPSG:4326]'

# ================= LOOP =================

for i in range(3, len(fields)):

    field_name = fields[i].name()
    safe_name = field_name.replace(" ", "_").replace("/", "_").replace("-", "_")

    print("Processing:", safe_name)

    try:
        processing.run("qgis:idwinterpolation", {
            'INTERPOLATION_DATA': f'{source}::~::0::~::{i}::~::0',
            'DISTANCE_COEFFICIENT': 2,
            'EXTENT': extent,
            'PIXEL_SIZE': 0.00001,   # чи өмнө хэрэглэж байсан
            'OUTPUT': f"{output_folder}/{safe_name}.tif"
        })

    except Exception as e:
        print(f"❌ ERROR on {safe_name}:", e)

print("FINISHED ✔ IDW үүслээ")
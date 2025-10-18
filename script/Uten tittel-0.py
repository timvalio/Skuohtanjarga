import os, re
from qgis.core import QgsProject, QgsVectorLayer
import processing

# ---- KONFIG ----
DIST_LAYER_HINT = "reinbeitedistrikt"   # navnedel på maskelaget (ZS-filtrert)
KEEP_KEYWORDS   = ["BygningerOgAnlegg", "Samferdsel", "Ledning"]  # hvilke N50-lag vi vil behandle
OUT_DIR         = r"C:\Users\timva\Documents\qgis2web\ZS_utklipp"  # mappe for utdata (shp)

# ---- HJELP ----
def find_layer(hint):
    for lyr in QgsProject.instance().mapLayers().values():
        if isinstance(lyr, QgsVectorLayer) and hint.lower() in lyr.name().lower():
            return lyr
    return None

def clean_name(qgis_layer_name):
    # ta bare delen etter "—"
    name = qgis_layer_name.split("—")[-1].strip() if "—" in qgis_layer_name else qgis_layer_name
    # fjern prefiks og spesialtegn
    name = re.sub(r"^N50[_-]*", "", name)
    rep = {"Æ":"Ae","Ø":"Oe","Å":"Aa","æ":"ae","ø":"oe","å":"aa"}
    name = "".join(rep.get(c,c) for c in name)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    # kort ned litt
    return (name[:40] or "lag")

# ---- SETUP ----
os.makedirs(OUT_DIR, exist_ok=True)

mask = find_layer(DIST_LAYER_HINT)
if not mask:
    raise RuntimeError(f"Fant ikke maskelag som matcher '{DIST_LAYER_HINT}'. Sjekk navnet i Lag-panelet.")

n50_layers = []
for lyr in QgsProject.instance().mapLayers().values():
    if isinstance(lyr, QgsVectorLayer) and "N50" in lyr.name() and any(k.lower() in lyr.name().lower() for k in KEEP_KEYWORDS):
        n50_layers.append(lyr)

if not n50_layers:
    raise RuntimeError("Fant ingen N50-lag i prosjektet som matcher nøkkelordene.")

print(f"▶ Skriver SHP til: {OUT_DIR}")
for lyr in n50_layers:
    out_base = clean_name(lyr.name())
    out_path = os.path.join(OUT_DIR, f"{out_base}.shp")
    # unngå låsing: fjern gammel fil hvis den finnes
    for ext in (".shp",".shx",".dbf",".prj",".cpg"):
        p = os.path.join(OUT_DIR, f"{out_base}{ext}")
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    print(f"  • {lyr.name()}  →  {out_base}.shp")
    if lyr.geometryType() == 2:  # polygon
        processing.run(
            "native:clip",
            {"INPUT": lyr, "OVERLAY": mask, "OUTPUT": out_path}
        )
    else:  # linje/punkt
        processing.run(
            "native:extractbylocation",
            {"INPUT": lyr, "PREDICATE": [0,1], "INTERSECT": mask, "OUTPUT": out_path}
        )

print("✅ Ferdig. Dra SHP-filene fra mappen inn i prosjektet.")

import os
import urllib.request

sf_dir = "data/soundfonts"
sf_path = os.path.join(sf_dir, "FluidR3_GM.sf2")
sf_url = "https://archive.org/download/fluidr3-gm/FluidR3_GM.sf2"

os.makedirs(sf_dir, exist_ok=True)

if not os.path.exists(sf_path):
    print("🎵 Baixando soundfont FluidR3_GM.sf2...")
    urllib.request.urlretrieve(sf_url, sf_path)
    print("✅ Soundfont baixada com sucesso.")
else:
    print("✅ Soundfont já existe.")
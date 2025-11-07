import streamlit as st
import tempfile
import os
import shutil
import json
from streamlit_javascript import st_javascript
import streamlit as st
from src.video_processing import video_note_split, midi_to_dict, count_channels, create_clip_unrestricted
import pandas as pd
from midi2audio import FluidSynth
import urllib.request

# -------------------
# INICIALIZAÇÃO DE SESSÃO
# -------------------
if "video_loaded" not in st.session_state:
    st.session_state.video_loaded = False
if "midi_loaded" not in st.session_state:
    st.session_state.midi_loaded = False

# Criar diretório temporário
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
print(f"Temporary directory: {st.session_state.temp_dir}")


def get_soundfont():
    sf_dir = "data/soundfonts"
    sf_path = os.path.join(sf_dir, "FluidR3_GM.sf2")
    if not os.path.exists(sf_path):
        os.makedirs(sf_dir, exist_ok=True)
        url = "https://archive.org/download/fluidr3-gm/FluidR3_GM.sf2"
        print("🎵 Baixando soundfont FluidR3_GM.sf2...")
        urllib.request.urlretrieve(url, sf_path)
        print("✅ Soundfont baixada.")
    return sf_path

#sf_path = get_soundfont()
fs = FluidSynth(sound_font="data/soundfonts/CP80_16_44100.sf2")


# -------------------
# CONFIGURAÇÃO DE LINGUAGEM
# -------------------
lang = st_javascript("navigator.language || navigator.userLanguage;")
if lang and lang.startswith("pt"):
    st.session_state.lang = "pt"
else:
    st.session_state.lang = "en"
with open("locales.json", "r") as f:
    LOCALES = json.load(f)

def t(key, lang="pt"):
    return LOCALES.get(lang, LOCALES["en"]).get(key, key)
#from src.processing import process_video_with_midi



# -------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------       


st.set_page_config(page_title=t("title", st.session_state.lang), layout="centered")
st.title(t("title", st.session_state.lang))


# -------------------
# UPLOAD OU ESCOLHA DE VÍDEO
# -------------------
st.markdown("---")  # separador
st.subheader(t("upload_video", st.session_state.lang))
v_header = t("video_hints_header", st.session_state.lang)

col1, col2 = st.columns([1, 1])
video_markdown = f"**{v_header}**"
for line in t("video_hints", st.session_state.lang).split("\n"):
    video_markdown += f"\n- {line.strip()}"
with col1:
    st.markdown(video_markdown)

    # Lista de vídeos da pasta data/instruments
    video_files = os.listdir("data/instruments")
    video_files = [f for f in video_files if f.lower().endswith(('.mp4', '.mov', '.avi'))]
    options = [t("upload_video", st.session_state.lang)] + video_files

    video_choice = st.selectbox(t("upload_video", st.session_state.lang), options, index=0)

    video_path = None
    uploaded_video = None

    if video_choice == t("upload_video", st.session_state.lang):
        uploaded_video = st.file_uploader(
            t("upload_video", st.session_state.lang),
            type=["mp4", "mov", "avi"]
        )
    else:
        shutil.copy(os.path.join("data", "instruments", video_choice), st.session_state.temp_dir)
        video_path = os.path.join(st.session_state.temp_dir, video_choice)

with col2:
    if uploaded_video is not None:
        st.video(uploaded_video)
        video_path = os.path.join(st.session_state.temp_dir, uploaded_video.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())
        st.success("✅ Vídeo carregado com sucesso!")
    elif video_path:
        st.video(video_path)
        st.success("✅ Vídeo selecionado com sucesso!")

# Processamento do vídeo
if video_path is not None:
    if "csv_path" not in st.session_state or st.session_state.video_name != os.path.basename(video_path):
        with st.spinner("⏳ Analisando notas, aguarde um ou mais minutos..."):
            csv_path = video_note_split(
                video_path,
                threshold=0.8, tune_thresh=0.3, dur_thresh=0.1,
                find_eyes=False, show_notes=False
            )
            df = pd.read_csv(csv_path)
            if len(df) == 0:
                st.error("❌ 0 Notas identificadas, escolha outro vídeo.")
            else:
                st.success(f"✅ Vídeo analisado, encontradas {len(df)} notas!")
                st.session_state.csv_path = csv_path
                st.session_state.video_name = os.path.basename(video_path)
                st.session_state.video_loaded = True
# -------------------
# ESCOLHA DE MIDI
# -------------------
# Opções: Upload + lista de arquivos da pasta midis
st.markdown("---")  # separador
st.subheader(t("upload_midi", st.session_state.lang))
col1, col2 = st.columns([1, 1])
midi_files = os.listdir("data/midis")
options = [t("upload_midi", st.session_state.lang)] + midi_files

midi = None
with col1:
    midi_choice = st.selectbox(t("upload_midi", st.session_state.lang), options, index=0)

    midi_path = None
    if midi_choice == t("upload_midi", st.session_state.lang):
        uploaded_midi = st.file_uploader("Envie um arquivo MIDI", type=["mid", "midi"])
        if uploaded_midi:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_midi:
                tmp_midi.write(uploaded_midi.read())
                midi_path = tmp_midi.name
    else:
        midi_path = os.path.join("data", "midis", midi_choice)
with col2:
    if midi_path:
        midi = midi_to_dict(midi_path, channel=None)
        print("MIDI lido com sucesso.")
        st.success("✅ MIDI lido com sucesso!")
        st.caption(f"Foram identificados os canais {count_channels(midi)}.")
        st.session_state.midi_loaded = True
        if st.session_state.midi_loaded:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                fs.midi_to_audio(midi_path, tmp_wav.name)

                # Mostra botão para tocar
                if st.button("▶️ Tocar"):
                    st.audio(tmp_wav.name)
        
# -------------------
# PROCESSAMENTO
# -------------------
st.markdown("---")  # separador
st.subheader("Escolha o formato do vídeo final:")
col1, col2 = st.columns([1, 1])

with col1:
    formato = st.radio(
        "Formato:",
        options=["Igual ao original", "Horizontal", "Vertical", "Quadrado"],
        index=0  # opção padrão
    )

    st.write("Formato selecionado:", formato)

    process = st.button("Gerar vídeo", disabled=not (st.session_state.video_loaded and st.session_state.midi_loaded))
    print(f"Process button clicked: {process}, video_loaded: {st.session_state.video_loaded}, midi_loaded: {st.session_state.midi_loaded}")

with col2:
    if process:
        with st.spinner("⏳ Processando, aguarde... Pode demorar muitos minutos..."):

            saved_video = create_clip_unrestricted(video_path, midi, save_name = "results.mp4", dur_mult=1,
                        imgshape=formato.lower(), autotune=True, fade_duration=0.05)    
            
            result_path = os.path.join(st.session_state.temp_dir, saved_video)

            if result_path is not None:
                st.video(result_path)
                with open(result_path, "rb") as f:
                    st.download_button("⬇️ Baixar vídeo", f, file_name="resultado.mp4", mime="video/mp4")
        

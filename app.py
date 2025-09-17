import streamlit as st
import tempfile
import os
import json
from streamlit_javascript import st_javascript
import streamlit as st
from src.video_processing import video_note_split, midi_to_dict, count_channels, create_clip_unrestricted



# Criar diretório temporário
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
print(f"Temporary directory: {st.session_state.temp_dir}")
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
# UPLOAD DE VÍDEO
# -------------------
st.markdown("---")  # separador
video_loaded = False
st.subheader(t("upload_video", st.session_state.lang))
v_header = t("video_hints_header", st.session_state.lang)

col1, col2 = st.columns([1, 1])
video_markdown = f"**{v_header}**"
for line in t("video_hints", st.session_state.lang).split("\n"):
    video_markdown += f"\n- {line.strip()}"
with col1:
    st.markdown(video_markdown)
    uploaded_video = st.file_uploader(t("upload_video", st.session_state.lang), type=["mp4", "mov", "avi"])
with col2:
    if uploaded_video is not None:
        st.video(uploaded_video)
        video_path = os.path.join(st.session_state.temp_dir, uploaded_video.name)
        print(video_path)
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())
        st.success("✅ Vídeo carregado com sucesso!")
        if "csv_path" not in st.session_state or st.session_state.video_name != uploaded_video.name:
            with st.spinner("⏳ Analisando notas, aguarde alguns minutos..."):
                csv_path = video_note_split(video_path, threshold=0.8, tune_thresh=0.3, dur_thresh=0.1,
                        find_eyes=False, show_notes=False)  
                st.success("✅ Pronto!")
                st.session_state.csv_path = csv_path
                st.session_state.video_name = uploaded_video.name
                video_loaded = True
        
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
midi_loaded = False
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
        midi_loaded = True
# -------------------
# PROCESSAMENTO
# -------------------
st.markdown("---")  # separador
st.subheader("Escolha o formato do vídeo final:")

formato = st.radio(
    "Formato:",
    options=["Horizontal", "Vertical", "Quadrado"],
    index=0  # opção padrão
)

st.write("Formato selecionado:", formato)

process = st.button("Gerar vídeo", disabled=not (video_loaded and midi_loaded))
print(f"Process button clicked: {process}, video_loaded: {video_loaded}, midi_loaded: {midi_loaded}")


if process:
    with st.spinner("⏳ Processando, aguarde... Pode demorar muitos minutos..."):

        saved_video = create_clip_unrestricted(video_path, midi, save_name = "results.mp4", dur_mult=1,
                    imgshape='vertical', autotune=True, fade_duration=0.05)    
        
        result_path = os.path.join(st.session_state.temp_dir, saved_video)

        if result_path is not None:
            st.video(result_path)
            with open(result_path, "rb") as f:
                st.download_button("⬇️ Baixar vídeo", f, file_name="resultado.mp4", mime="video/mp4")
    

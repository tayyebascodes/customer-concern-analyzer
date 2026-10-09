"""
app.py - V2V: Voice-to-Voice Customer Intelligence Ecosystem
Theme: Hitit (Awwwards Nominee by ADAM Creative)
Features:
  - Context-Conscious Active Conversation Memory (multi-turn dialogue continuity)
  - Dynamic Hitit Aerospace UI: glowing pill tabs (no default underlines), animated buttons
  - Paper plane sending action button (✈️ Send Voice Message)
  - 100% Free & Local Stack: Whisper STT + Google Gemini + gTTS + SQLite
"""

import os
import shutil
import logging
from datetime import datetime

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use Windows Certificate Store for SSL verification
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# Ensure FFmpeg is accessible on Windows
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

scripts_dir = os.path.join(os.path.dirname(__file__), "venv", "Scripts")
if os.path.exists(scripts_dir) and scripts_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = scripts_dir + os.pathsep + os.environ.get("PATH", "")

# Import internal modules
import importlib
import database as db
import pipeline

try:
    importlib.reload(pipeline)
    importlib.reload(db)
except Exception:
    pass

logger = logging.getLogger(__name__)

# Check for audio recorder component
try:
    from audio_recorder_streamlit import audio_recorder
    HAS_AUDIO_RECORDER = True
except ImportError:
    HAS_AUDIO_RECORDER = False

# Page configuration
st.set_page_config(
    page_title="V2V — Voice-to-Voice Intelligence Ecosystem",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database
db.init_db()

# Initialize session state for multi-turn conversation memory
if "conversation_thread" not in st.session_state:
    st.session_state["conversation_thread"] = []

# ---------------------------------------------------------
# Hitit Awwwards Design System (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&family=Urbanist:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap" rel="stylesheet">

    <style>
    /* Hitit Deep Obsidian Space Canvas */
    .stApp {
        background-color: #07090E !important;
        background-image: 
            radial-gradient(circle at 15% 10%, rgba(14, 165, 233, 0.12) 0%, transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(249, 115, 22, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 50% 90%, rgba(16, 185, 129, 0.06) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #E2E8F0 !important;
    }

    /* Clean Content Container */
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1160px !important;
    }

    /* Hide Sidebar Collapse Button */
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Hitit Header & Brand Pill */
    .hitit-header {
        margin-bottom: 2.2rem;
    }
    .hitit-telemetry-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #38BDF8;
        margin-bottom: 1rem;
        backdrop-filter: blur(12px);
    }
    .pulse-dot {
        width: 7px;
        height: 7px;
        background-color: #38BDF8;
        border-radius: 50%;
        box-shadow: 0 0 10px #38BDF8;
        animation: pulseAnimation 2s infinite ease-in-out;
    }
    @keyframes pulseAnimation {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.75); }
    }

    .hitit-title {
        font-family: 'Urbanist', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        line-height: 1.08;
        letter-spacing: -0.035em;
        color: #FFFFFF;
        margin: 0 0 0.8rem 0;
        background: linear-gradient(180deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hitit-subtitle {
        font-size: 1.02rem;
        font-weight: 400;
        line-height: 1.6;
        color: #94A3B8;
        max-width: 720px;
        margin: 0;
    }

    /* Hitit Dynamic Segmented Pill Tabs (Fixes default red underline) */
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        display: none !important;
        height: 0 !important;
        background-color: transparent !important;
        border: none !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: rgba(14, 18, 27, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 9999px !important;
        padding: 5px !important;
        gap: 6px !important;
        width: fit-content !important;
        margin-bottom: 2rem !important;
        backdrop-filter: blur(20px) !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 9999px !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #94A3B8 !important;
        padding: 9px 24px !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
        color: #F8FAFC !important;
        background: rgba(255, 255, 255, 0.06) !important;
        transform: translateY(-1px) !important;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 1px solid rgba(56, 189, 248, 0.45) !important;
        box-shadow: 0 4px 18px rgba(2, 132, 199, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
        transform: translateY(-1px) !important;
    }

    /* Dynamic Aerospace Send & Action Buttons */
    .stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 10px !important;
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
        border: 1px solid rgba(56, 189, 248, 0.5) !important;
        border-radius: 9999px !important;
        padding: 0.72rem 2.2rem !important;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%) !important;
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 30px rgba(14, 165, 233, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
        border-color: #38BDF8 !important;
    }
    .stButton > button:active {
        transform: translateY(1px) scale(0.98) !important;
        box-shadow: 0 2px 10px rgba(2, 132, 199, 0.3) !important;
    }

    /* Glassmorphic Container Cards */
    .hitit-card {
        background: rgba(14, 18, 27, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 1.8rem !important;
        backdrop-filter: blur(24px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
        box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        margin-bottom: 1.5rem !important;
    }
    .hitit-card-title {
        font-family: 'Urbanist', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        margin-bottom: 0.5rem;
    }

    /* Dialogue Thread Turn Card */
    .dialogue-turn-card {
        background: rgba(18, 24, 38, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        position: relative;
    }
    .dialogue-turn-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .dialogue-bubble-user {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 12px;
        padding: 12px 16px;
        color: #E2E8F0;
        margin-bottom: 1rem;
        font-style: italic;
    }
    .dialogue-bubble-ai {
        background: rgba(2, 132, 199, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 14px 18px;
        color: #F8FAFC;
        line-height: 1.6;
    }

    /* Streamlit Input Overrides for Deep Obsidian */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: rgba(18, 24, 36, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #F8FAFC !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.95rem !important;
        transition: border-color 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.18) !important;
    }

    /* Urgency Badges */
    .hitit-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .badge-high {
        background: rgba(239, 68, 68, 0.12) !important;
        color: #F87171 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
    .badge-medium {
        background: rgba(245, 158, 11, 0.12) !important;
        color: #FBBF24 !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }
    .badge-low {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #34D399 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    /* Expanders & Settings */
    [data-testid="stExpander"] {
        background: rgba(14, 18, 27, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        margin-bottom: 1rem !important;
    }

    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-family: 'Urbanist', sans-serif !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        letter-spacing: -0.03em !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }

    hr {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        margin: 2rem 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Hitit Hero Header
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hitit-header">
        <div class="hitit-telemetry-pill">
            <span class="pulse-dot"></span>
            <span>V2V INTELLIGENCE ECOSYSTEM</span>
        </div>
        <h1 class="hitit-title">V2V</h1>
        <p class="hitit-subtitle">
            Voice-to-Voice Autonomous Customer Intelligence: continuous thread memory across follow-ups, offline Whisper STT, and Google Gemini reasoning.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Settings Panel (Unobtrusive Expander)
# ---------------------------------------------------------
biz_context = "Airlines, Aviation Operations, B2B Enterprise Technology, Booking Infrastructure, and Customer Operations"

with st.expander("System Configuration & Business Profile", expanded=False):
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        env_gemini_key = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input(
            "Gemini API Key:",
            value=env_gemini_key,
            type="password",
            help="Securely loaded from .env. Override here if needed.",
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input

        model_choice = st.selectbox(
            "Intelligence Engine:",
            options=["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"],
            index=0,
        )
        os.environ["GEMINI_MODEL"] = model_choice

    with c_s2:
        biz_context = st.text_area(
            "Domain Profile Context:",
            value=biz_context,
            help="Domain guidelines to steer intent recognition and response tone.",
            height=95,
        )

# ---------------------------------------------------------
# Hitit Navigation Tabs
# ---------------------------------------------------------
tab_studio, tab_records = st.tabs(["Voice Capture", "Intelligence Archives"])


# =========================================================
# TAB 1: VOICE CAPTURE (CONTEXT-CONSCIOUS DIALOGUE)
# =========================================================
with tab_studio:
    # Context Consciousness Thread Status Indicator
    thread_len = len(st.session_state["conversation_thread"])
    if thread_len > 0:
        latest_org = st.session_state["conversation_thread"][-1]["organization"]
        t_col1, t_col2 = st.columns([3, 1])
        with t_col1:
            st.markdown(
                f"""
                <div style="background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(56, 189, 248, 0.28); border-radius: 12px; padding: 10px 16px; margin-bottom: 1.2rem; display: flex; align-items: center; gap: 10px;">
                    <span class="pulse-dot"></span>
                    <span style="color: #38BDF8; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.05em; text-transform: uppercase;">ACTIVE CONVERSATION THREAD</span>
                    <span style="color: #CBD5E1; font-size: 0.85rem;">— <b>{latest_org}</b> ({thread_len} turn{'s' if thread_len > 1 else ''} remembered)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with t_col2:
            if st.button("↺ Start New Thread", key="reset_dialogue"):
                st.session_state["conversation_thread"] = []
                st.session_state.pop("last_result", None)
                st.toast("Conversation thread reset for new customer interaction.", icon="🔄")
                st.rerun()

    st.markdown("##### Audio Source Stream")
    input_method = st.radio(
        "Source Stream:",
        ["Live Microphone Input", "Audio File Upload (.wav, .mp3, .m4a)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    audio_bytes = None

    if input_method == "Live Microphone Input":
        if HAS_AUDIO_RECORDER:
            st.caption("Press to record audio signal, speak clearly, then press again to complete stream:")
            col_rec, _ = st.columns([1, 4])
            with col_rec:
                recorded_audio = audio_recorder(
                    text="Record Audio Stream",
                    recording_color="#F43F5E",
                    neutral_color="#38BDF8",
                    icon_name="microphone",
                    icon_size="2x",
                )
            if recorded_audio:
                audio_bytes = recorded_audio
                st.audio(audio_bytes, format="audio/wav")
        else:
            st.info("Live microphone component unavailable. Upload an audio stream file below:")
            uploaded_file = st.file_uploader("Upload audio signal", type=["wav", "mp3", "m4a", "ogg"])
            if uploaded_file is not None:
                audio_bytes = uploaded_file.read()
                st.audio(audio_bytes)
    else:
        uploaded_file = st.file_uploader("Upload client audio stream file", type=["wav", "mp3", "m4a", "ogg"])
        if uploaded_file is not None:
            audio_bytes = uploaded_file.read()
            st.audio(audio_bytes)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Dynamic Send Action Button (Paper plane icon)
    col_action, _ = st.columns([1, 4])
    with col_action:
        run_analysis = st.button("✈️ Send Voice Message", type="primary", use_container_width=True)

    if run_analysis:
        if not audio_bytes:
            st.error("Audio signal missing. Please record or upload an audio file first.")
        elif not os.getenv("GEMINI_API_KEY"):
            st.error("Gemini API key is required. Please set it in System Configuration.")
        else:
            with st.status("Executing Intelligence Pipeline with Thread Context...", expanded=True) as status_box:
                try:
                    # 1. Local STT
                    status_box.update(label="1/3 Transcribing audio stream with local Whisper...", state="running")
                    transcript = pipeline.transcribe_audio_bytes(audio_bytes)

                    # 2. Gemini Analysis with active conversation history
                    status_box.update(label="2/3 Grounding against active dialogue thread & history...", state="running")
                    history_summary = db.get_recent_summary_context(limit=5)
                    try:
                        analysis = pipeline.analyze_transcript_with_gemini(
                            transcript,
                            business_context=biz_context,
                            history_context=history_summary,
                            conversation_history=st.session_state["conversation_thread"],
                        )
                    except TypeError as te:
                        if "conversation_history" in str(te):
                            analysis = pipeline.analyze_transcript_with_gemini(
                                transcript,
                                business_context=biz_context,
                                history_context=history_summary,
                            )
                        else:
                            raise

                    # 3. Speech Synthesis
                    status_box.update(label="3/3 Synthesizing outbound acoustic response...", state="running")
                    audio_out_path = pipeline.synthesize_speech_gtts(analysis["drafted_response"])

                    # 4. Storage in SQLite
                    record_id = db.insert_concern(
                        organization=analysis["organization"],
                        urgency=analysis["urgency"],
                        core_concerns=analysis["core_concerns"],
                        transcript=transcript,
                        drafted_response=analysis["drafted_response"],
                        audio_path=audio_out_path,
                    )

                    # 5. Append to Active Conversation Thread
                    turn_data = {
                        "turn_id": len(st.session_state["conversation_thread"]) + 1,
                        "id": record_id,
                        "organization": analysis["organization"],
                        "urgency": analysis["urgency"],
                        "core_concerns": analysis["core_concerns"],
                        "user_transcript": transcript,
                        "drafted_response": analysis["drafted_response"],
                        "audio_path": audio_out_path,
                        "timestamp": datetime.now().strftime("%I:%M %p"),
                    }
                    st.session_state["conversation_thread"].append(turn_data)
                    st.session_state["last_result"] = turn_data

                    status_box.update(label=f"Turn #{turn_data['turn_id']} processed & remembered.", state="complete", expanded=False)
                    st.toast(f"Intelligence logged — Turn #{turn_data['turn_id']} saved!", icon="✈️")

                except Exception as ex:
                    logger.exception("Pipeline processing error")
                    status_box.update(label="Pipeline execution failed.", state="error")
                    st.error(f"Execution error: {str(ex)}")

    # ---------------------------------------------------------
    # Render Active Continuous Conversation Thread
    # ---------------------------------------------------------
    if st.session_state["conversation_thread"]:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Ongoing Customer Dialogue")
        st.caption("The AI retains memory of all previous turns in this thread to address evolving demands and follow-up questions contextually.")

        # Show dialogue turns in chronological order
        for turn in st.session_state["conversation_thread"]:
            urgency_lower = turn["urgency"].lower()
            badge_class = f"badge-{urgency_lower}"

            st.markdown(
                f"""
                <div class="dialogue-turn-card">
                    <div class="dialogue-turn-header">
                        <div>
                            <span style="font-family: 'Urbanist', sans-serif; font-weight: 800; font-size: 1.15rem; color: #FFFFFF;">
                                Turn #{turn['turn_id']} — {turn['organization']}
                            </span>
                            <span style="color: #64748B; font-size: 0.85rem; margin-left: 10px;">{turn['timestamp']} (Case #{turn['id']})</span>
                        </div>
                        <div>
                            <span class="hitit-badge {badge_class}">{turn['urgency']} Urgency</span>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            col_t_left, col_t_right = st.columns(2)

            with col_t_left:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;'>🗣️ Customer Speech</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dialogue-bubble-user'>\"{turn['user_transcript']}\"</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;'>🎯 Extracted Demands & Concerns</div>", unsafe_allow_html=True)
                for concern in turn["core_concerns"]:
                    st.markdown(f"<div style='color: #CBD5E1; margin-bottom: 4px; font-size: 0.92rem;'><span style='color: #38BDF8;'>▹</span> {concern}</div>", unsafe_allow_html=True)

            with col_t_right:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;'>✈️ Context-Aware Response</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dialogue-bubble-ai'>\"{turn['drafted_response']}\"</div>", unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if os.path.exists(turn["audio_path"]):
                    with open(turn["audio_path"], "rb") as af:
                        audio_data = af.read()
                    st.audio(audio_data, format="audio/mp3")
                    st.download_button(
                        label=f"Download Response #{turn['turn_id']} (.mp3)",
                        data=audio_data,
                        file_name=os.path.basename(turn["audio_path"]),
                        mime="audio/mp3",
                        key=f"dl_turn_{turn['turn_id']}",
                    )
                else:
                    st.caption("Acoustic file not found on disk.")

            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# TAB 2: INTELLIGENCE ARCHIVES
# =========================================================
with tab_records:
    records = db.get_all_concerns()

    if not records:
        st.info("No recorded customer intelligence files found. Run a voice capture to populate archives.")
    else:
        # Key Global Metrics
        total_count = len(records)
        high_count = sum(1 for r in records if r["urgency"] == "High")
        med_count = sum(1 for r in records if r["urgency"] == "Medium")
        low_count = sum(1 for r in records if r["urgency"] == "Low")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Ecosystem Cases", total_count)
        m2.metric("Critical Urgency", high_count)
        m3.metric("Medium Urgency", med_count)
        m4.metric("Standard Urgency", low_count)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Filters
        flt_col1, flt_col2 = st.columns([3, 1])
        with flt_col1:
            search_query = st.text_input("Filter Ecosystem Records:", placeholder="Search by organization, key term, or transcript...")
        with flt_col2:
            urgency_filter = st.selectbox("Urgency Index:", ["All", "High", "Medium", "Low"])

        filtered = records
        if urgency_filter != "All":
            filtered = [r for r in filtered if r["urgency"] == urgency_filter]
        if search_query:
            q = search_query.lower()
            filtered = [
                r for r in filtered
                if q in r["organization"].lower()
                or q in r["transcript"].lower()
                or q in str(r["core_concerns"]).lower()
            ]

        st.caption(f"Displaying {len(filtered)} of {total_count} archived records")

        # Archive Card List
        for rec in filtered:
            urgency_lower = rec["urgency"].lower()
            badge_class = f"badge-{urgency_lower}"

            with st.expander(f"Case #{rec['id']} — {rec['organization']} [{rec['urgency']}] — {rec['timestamp']}"):
                r_c1, r_c2 = st.columns([3, 1])
                with r_c1:
                    st.markdown(f"**Enterprise:** {rec['organization']}")
                    st.caption(f"Timestamp: {rec['timestamp']}")
                with r_c2:
                    st.markdown(
                        f'<div style="text-align: right;"><span class="hitit-badge {badge_class}">{rec["urgency"]} Urgency</span></div>',
                        unsafe_allow_html=True,
                    )

                c_left, c_right = st.columns(2)
                with c_left:
                    st.markdown("**Transcript:**")
                    st.write(f"\"{rec['transcript']}\"")

                    st.markdown("**Core Concerns:**")
                    for c in rec["core_concerns_list"]:
                        st.markdown(f"▹ {c}")

                with c_right:
                    st.markdown("**Drafted Response:**")
                    st.write(f"\"{rec['drafted_response']}\"")

                    st.markdown("**Acoustic Replay:**")
                    if os.path.exists(rec["audio_path"]):
                        with open(rec["audio_path"], "rb") as f:
                            past_audio = f.read()
                        st.audio(past_audio, format="audio/mp3")
                    else:
                        st.caption("Acoustic record not found.")

                del_col, _ = st.columns([1, 5])
                with del_col:
                    if st.button("Delete Case Record", key=f"del_{rec['id']}"):
                        db.delete_concern(rec["id"])
                        if os.path.exists(rec["audio_path"]):
                            try:
                                os.remove(rec["audio_path"])
                            except Exception:
                                pass
                        st.success(f"Case #{rec['id']} purged.")
                        st.rerun()

"""
app.py - Customer Concern Analyzer
Theme: Hitit (Awwwards Nominee by ADAM Creative)
Aviation & Aerospace-Grade AI Interface:
  - Deep obsidian & dark slate canvas with ethereal aurora ambient glow
  - Manrope & Urbanist modern geometric typography
  - Floating pill navigation & frosted dark glassmorphic cards
  - Real-time pulse telemetry & high-contrast intelligence analytics
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
import database as db
import pipeline

logger = logging.getLogger(__name__)

# Check for audio recorder component
try:
    from audio_recorder_streamlit import audio_recorder
    HAS_AUDIO_RECORDER = True
except ImportError:
    HAS_AUDIO_RECORDER = False

# Page configuration
st.set_page_config(
    page_title="Hitit — Customer Intelligence Ecosystem",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database
db.init_db()

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
        margin-bottom: 2.5rem;
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
        margin-bottom: 1.2rem;
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
        font-size: 3.1rem;
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
        font-size: 1.05rem;
        font-weight: 400;
        line-height: 1.6;
        color: #94A3B8;
        max-width: 700px;
        margin: 0;
    }

    /* Hitit Aerospace Glassmorphism Card */
    .hitit-card {
        background: rgba(14, 18, 27, 0.72) !important;
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

    /* Hitit Minimalist Pill Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 9999px !important;
        padding: 4px !important;
        gap: 6px !important;
        width: fit-content !important;
        margin-bottom: 2rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        color: #94A3B8 !important;
        border: none !important;
        padding: 8px 24px !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #07090E !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 20px rgba(255, 255, 255, 0.18) !important;
    }

    /* Hitit Signature Button (White inverted pill) */
    .stButton > button {
        background: #FFFFFF !important;
        color: #07090E !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 0.68rem 2.2rem !important;
        box-shadow: 0 4px 24px rgba(255, 255, 255, 0.15) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button:hover {
        background: #E2E8F0 !important;
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 8px 30px rgba(255, 255, 255, 0.28) !important;
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

    /* Urgency Aviation Badges */
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

    /* Clean Horizontal Dividers */
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
            <span>Aviation-Grade Customer Intelligence</span>
        </div>
        <h1 class="hitit-title">Crafting Clarity from <br>Every Voice Interaction</h1>
        <p class="hitit-subtitle">
            Autonomous audio capture, offline Whisper transcription, and structured concern discovery powered by Google Gemini.
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
# TAB 1: VOICE CAPTURE
# =========================================================
with tab_studio:
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

    col_action, _ = st.columns([1, 4])
    with col_action:
        run_analysis = st.button("Analyze Audio Stream", type="primary", use_container_width=True)

    if run_analysis:
        if not audio_bytes:
            st.error("Audio signal missing. Please record or upload an audio file first.")
        elif not os.getenv("GEMINI_API_KEY"):
            st.error("Gemini API key is required. Please set it in System Configuration.")
        else:
            with st.status("Executing Intelligence Pipeline...", expanded=True) as status_box:
                try:
                    # 1. Local STT
                    status_box.update(label="1/3 Transcribing audio stream with local Whisper...", state="running")
                    transcript = pipeline.transcribe_audio_bytes(audio_bytes)

                    # 2. Gemini Analysis
                    status_box.update(label="2/3 Grounding concerns & drafting reply with Gemini...", state="running")
                    history_summary = db.get_recent_summary_context(limit=5)
                    analysis = pipeline.analyze_transcript_with_gemini(
                        transcript,
                        business_context=biz_context,
                        history_context=history_summary,
                    )

                    # 3. Speech Synthesis
                    status_box.update(label="3/3 Synthesizing outbound acoustic response...", state="running")
                    audio_out_path = pipeline.synthesize_speech_gtts(analysis["drafted_response"])

                    # 4. Storage
                    record_id = db.insert_concern(
                        organization=analysis["organization"],
                        urgency=analysis["urgency"],
                        core_concerns=analysis["core_concerns"],
                        transcript=transcript,
                        drafted_response=analysis["drafted_response"],
                        audio_path=audio_out_path,
                    )

                    status_box.update(label="Pipeline completed and stored.", state="complete", expanded=False)
                    st.toast(f"Intelligence logged as Case #{record_id}", icon="✈️")

                    st.session_state["last_result"] = {
                        "id": record_id,
                        "organization": analysis["organization"],
                        "urgency": analysis["urgency"],
                        "core_concerns": analysis["core_concerns"],
                        "transcript": transcript,
                        "drafted_response": analysis["drafted_response"],
                        "audio_path": audio_out_path,
                    }

                except Exception as ex:
                    logger.exception("Pipeline processing error")
                    status_box.update(label="Pipeline execution failed.", state="error")
                    st.error(f"Execution error: {str(ex)}")

    # ---------------------------------------------------------
    # Structured Intelligence Result Presentation
    # ---------------------------------------------------------
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        urgency_lower = res["urgency"].lower()
        badge_class = f"badge-{urgency_lower}"

        st.markdown("<hr>", unsafe_allow_html=True)

        hdr_l, hdr_r = st.columns([3, 1])
        with hdr_l:
            st.markdown(
                f"""
                <div style="font-family: 'Urbanist', sans-serif; font-size: 1.8rem; font-weight: 800; color: #FFFFFF;">
                    {res['organization']} 
                    <span style="font-size: 0.95rem; font-weight: 500; color: #64748B; margin-left: 8px;">Case #{res['id']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with hdr_r:
            st.markdown(
                f'<div style="text-align: right; padding-top: 6px;"><span class="hitit-badge {badge_class}">{res["urgency"]} Urgency</span></div>',
                unsafe_allow_html=True,
            )

        col_trans, col_resp = st.columns(2)

        with col_trans:
            st.markdown(
                """
                <div class="hitit-card">
                    <div class="hitit-card-title">Customer Signal Transcript</div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"<p style='color: #CBD5E1; font-size: 1rem; line-height: 1.6; font-style: italic;'>\"{res['transcript']}\"</p>", unsafe_allow_html=True)
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='hitit-card-title'>Extracted Core Concerns</div>", unsafe_allow_html=True)
            for item in res["core_concerns"]:
                st.markdown(f"<div style='color: #94A3B8; margin-bottom: 6px;'><span style='color: #38BDF8;'>▹</span> {item}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_resp:
            st.markdown(
                """
                <div class="hitit-card">
                    <div class="hitit-card-title">Synthesized Outbound Response</div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px; color: #F1F5F9; line-height: 1.6;'>\"{res['drafted_response']}\"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='hitit-card-title'>Acoustic Replay</div>", unsafe_allow_html=True)

            if os.path.exists(res["audio_path"]):
                with open(res["audio_path"], "rb") as audio_file:
                    audio_bytes_out = audio_file.read()
                st.audio(audio_bytes_out, format="audio/mp3")

                st.download_button(
                    label="Download Audio Track (.mp3)",
                    data=audio_bytes_out,
                    file_name=os.path.basename(res["audio_path"]),
                    mime="audio/mp3",
                )
            else:
                st.warning("Audio file unavailable on local storage.")

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

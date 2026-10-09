"""
app.py - Customer Concern Analyzer
Clean, minimal, and direct voice intelligence dashboard.
Features:
  - Direct audio capture (microphone or file upload)
  - Offline transcription with Whisper
  - Structured concern extraction & response generation with Gemini
  - Local voice synthesis with gTTS
  - Local SQLite history & search
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

# Page configuration - No sidebar by default
st.set_page_config(
    page_title="Customer Concern Analyzer",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize database
db.init_db()

# Clean, modern, minimalist CSS
st.markdown(
    """
    <style>
    /* Clean modern typography and background */
    .stApp {
        background-color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #1E293B;
    }
    
    /* Clean content container */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1050px !important;
    }

    /* Hide sidebar collapse button */
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* App Header */
    .app-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .app-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .app-subtitle {
        font-size: 0.95rem;
        color: #64748B;
        margin-top: 0.25rem;
    }

    /* Clean Card */
    .clean-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
    }

    /* Badges */
    .urgency-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .urgency-high {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
    }
    .urgency-medium {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
    }
    .urgency-low {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }

    /* Clean buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# App Header
st.markdown(
    """
    <div class="app-header">
        <h1 class="app-title">Customer Concern Analyzer</h1>
        <p class="app-subtitle">Capture customer voice messages, analyze concerns with AI, and generate audio responses.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Default configuration settings
biz_context = "B2B Enterprise Software, Cloud Infrastructure, Technical Solutions, and Billing Operations"

# Optional Settings Expander (Uncluttered, collapsed by default)
with st.expander("Settings & Business Context", expanded=False):
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        env_gemini_key = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input(
            "Gemini API Key:",
            value=env_gemini_key,
            type="password",
            help="Configured in your .env file.",
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input

        model_choice = st.selectbox(
            "Gemini Model Tier:",
            options=["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"],
            index=0,
        )
        os.environ["GEMINI_MODEL"] = model_choice

    with s_col2:
        biz_context = st.text_area(
            "Business Context Profile:",
            value=biz_context,
            help="Domain context to ground the AI in your company's workflows.",
            height=100,
        )

# Navigation Tabs
tab_analyze, tab_history = st.tabs(["Analyze Audio", "Case History"])


# =========================================================
# TAB 1: ANALYZE AUDIO
# =========================================================
with tab_analyze:
    st.markdown("##### Audio Input")
    input_method = st.radio(
        "Audio Source:",
        ["Live Microphone", "Upload Audio File (.wav, .mp3, .m4a)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    audio_bytes = None

    if input_method == "Live Microphone":
        if HAS_AUDIO_RECORDER:
            st.caption("Click to record, speak your message, then click again to stop:")
            col_rec, _ = st.columns([1, 4])
            with col_rec:
                recorded_audio = audio_recorder(
                    text="Record Voice",
                    recording_color="#EF4444",
                    neutral_color="#64748B",
                    icon_name="microphone",
                    icon_size="2x",
                )
            if recorded_audio:
                audio_bytes = recorded_audio
                st.audio(audio_bytes, format="audio/wav")
        else:
            st.info("Live microphone component not installed. Upload an audio file below:")
            uploaded_file = st.file_uploader("Upload audio file", type=["wav", "mp3", "m4a", "ogg"])
            if uploaded_file is not None:
                audio_bytes = uploaded_file.read()
                st.audio(audio_bytes)
    else:
        uploaded_file = st.file_uploader("Upload customer audio", type=["wav", "mp3", "m4a", "ogg"])
        if uploaded_file is not None:
            audio_bytes = uploaded_file.read()
            st.audio(audio_bytes)

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        run_analysis = st.button("Analyze Concern", type="primary", use_container_width=True)

    if run_analysis:
        if not audio_bytes:
            st.error("Please record or upload an audio file first.")
        elif not os.getenv("GEMINI_API_KEY"):
            st.error("Gemini API key is required. Please set it in Settings.")
        else:
            with st.status("Processing audio...", expanded=True) as status_box:
                try:
                    # Step 1: STT
                    status_box.update(label="Transcribing audio with Whisper...", state="running")
                    transcript = pipeline.transcribe_audio_bytes(audio_bytes)

                    # Step 2: Concern Analysis
                    status_box.update(label="Analyzing concerns with Gemini...", state="running")
                    history_summary = db.get_recent_summary_context(limit=5)
                    analysis = pipeline.analyze_transcript_with_gemini(
                        transcript,
                        business_context=biz_context,
                        history_context=history_summary,
                    )

                    # Step 3: Outbound Voice Generation
                    status_box.update(label="Generating audio response...", state="running")
                    audio_out_path = pipeline.synthesize_speech_gtts(analysis["drafted_response"])

                    # Step 4: Database Save
                    record_id = db.insert_concern(
                        organization=analysis["organization"],
                        urgency=analysis["urgency"],
                        core_concerns=analysis["core_concerns"],
                        transcript=transcript,
                        drafted_response=analysis["drafted_response"],
                        audio_path=audio_out_path,
                    )

                    status_box.update(label="Analysis completed.", state="complete", expanded=False)
                    st.toast(f"Saved case #{record_id}", icon="✅")

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
                    logger.exception("Pipeline error occurred")
                    status_box.update(label="Analysis failed.", state="error")
                    st.error(f"Error during processing: {str(ex)}")

    # Display Analysis Result
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        urgency_lower = res["urgency"].lower()
        badge_class = f"urgency-{urgency_lower}"

        st.markdown("---")

        h_col1, h_col2 = st.columns([3, 1])
        with h_col1:
            st.markdown(f"### {res['organization']} `Case #{res['id']}`")
        with h_col2:
            st.markdown(
                f'<div style="text-align: right; padding-top: 8px;"><span class="urgency-badge {badge_class}">{res["urgency"]} Urgency</span></div>',
                unsafe_allow_html=True,
            )

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("##### Customer Transcript")
            st.info(f"\"{res['transcript']}\"")

            st.markdown("##### Core Concerns")
            for concern in res["core_concerns"]:
                st.markdown(f"• {concern}")

        with col_right:
            st.markdown("##### Drafted Response")
            st.success(f"\"{res['drafted_response']}\"")

            st.markdown("##### Audio Response")
            if os.path.exists(res["audio_path"]):
                with open(res["audio_path"], "rb") as audio_file:
                    audio_bytes_out = audio_file.read()
                st.audio(audio_bytes_out, format="audio/mp3")

                st.download_button(
                    label="Download Audio (.mp3)",
                    data=audio_bytes_out,
                    file_name=os.path.basename(res["audio_path"]),
                    mime="audio/mp3",
                )
            else:
                st.warning("Audio file could not be located on disk.")


# =========================================================
# TAB 2: CASE HISTORY
# =========================================================
with tab_history:
    records = db.get_all_concerns()

    if not records:
        st.info("No customer concerns recorded yet. Analyze an audio message to begin.")
    else:
        # Summary Metrics
        total_count = len(records)
        high_count = sum(1 for r in records if r["urgency"] == "High")
        med_count = sum(1 for r in records if r["urgency"] == "Medium")
        low_count = sum(1 for r in records if r["urgency"] == "Low")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Cases", total_count)
        m2.metric("High Urgency", high_count)
        m3.metric("Medium Urgency", med_count)
        m4.metric("Low Urgency", low_count)

        st.markdown("---")

        # Search and Urgency Filter
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            search_query = st.text_input("Search Cases:", placeholder="Search by organization, concern, or transcript text...")
        with fc2:
            urgency_filter = st.selectbox("Urgency Filter:", ["All", "High", "Medium", "Low"])

        filtered_records = records
        if urgency_filter != "All":
            filtered_records = [r for r in filtered_records if r["urgency"] == urgency_filter]
        if search_query:
            q = search_query.lower()
            filtered_records = [
                r for r in filtered_records
                if q in r["organization"].lower()
                or q in r["transcript"].lower()
                or q in str(r["core_concerns"]).lower()
            ]

        st.caption(f"Showing {len(filtered_records)} of {total_count} cases")

        # Case Records List
        for rec in filtered_records:
            urgency_lower = rec["urgency"].lower()
            badge_class = f"urgency-{urgency_lower}"

            with st.expander(f"Case #{rec['id']} — {rec['organization']} [{rec['urgency']}] — {rec['timestamp']}"):
                col_info, col_badge = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**Organization:** {rec['organization']}")
                    st.caption(f"Logged at: {rec['timestamp']}")
                with col_badge:
                    st.markdown(
                        f'<div style="text-align: right;"><span class="urgency-badge {badge_class}">{rec["urgency"]} Urgency</span></div>',
                        unsafe_allow_html=True,
                    )

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Transcript:**")
                    st.write(f"\"{rec['transcript']}\"")

                    st.markdown("**Core Concerns:**")
                    for c in rec["core_concerns_list"]:
                        st.markdown(f"• {c}")

                with c2:
                    st.markdown("**Drafted Response:**")
                    st.write(f"\"{rec['drafted_response']}\"")

                    st.markdown("**Outbound Audio:**")
                    if os.path.exists(rec["audio_path"]):
                        with open(rec["audio_path"], "rb") as f:
                            past_audio = f.read()
                        st.audio(past_audio, format="audio/mp3")
                    else:
                        st.caption(f"Audio file `{rec['audio_path']}` is not found.")

                del_col, _ = st.columns([1, 5])
                with del_col:
                    if st.button("Delete Case", key=f"del_{rec['id']}"):
                        db.delete_concern(rec["id"])
                        if os.path.exists(rec["audio_path"]):
                            try:
                                os.remove(rec["audio_path"])
                            except Exception:
                                pass
                        st.success(f"Case #{rec['id']} deleted.")
                        st.rerun()

"""
pipeline.py - Core AI Pipeline for Customer Concern Analyzer.
Orchestrates:
  Step A: Local Speech-to-Text via OpenAI Whisper ('base' model, 100% offline).
  Step B: Structured Analysis via Google Gemini Flash-Lite ('google-genai' SDK).
  Step C: Text-to-Speech via gTTS (Local Google Text-to-Speech).
"""

import os
import re
import json
import uuid
import tempfile
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use Windows Certificate Store for SSL verification (resolves SSL: CERTIFICATE_VERIFY_FAILED on Windows)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# Ensure FFmpeg is accessible on Windows (from venv/Scripts or imageio_ffmpeg)
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

# Global cache for the Whisper model so it is loaded only once per session
_WHISPER_MODEL = None


class ConcernAnalysis(BaseModel):
    """Structured Pydantic schema for Gemini analysis output."""
    organization: str = Field(
        description="The name of the client organization or company. Use 'Unknown Client' if unspecified."
    )
    core_concerns: list[str] = Field(
        description="Concise bullet-point list detailing the specific customer issues, complaints, or questions."
    )
    urgency: str = Field(
        description="Priority urgency level: exactly 'Low', 'Medium', or 'High' based on emotional tone, business risk, and context."
    )
    drafted_response: str = Field(
        description="A professional, empathetic, spoken-style response suitable for direct audio voice playback back to the customer."
    )


def load_whisper_model(model_name: str = "base"):
    """
    Loads and caches the local OpenAI Whisper model.
    Runs 100% locally and offline without external API calls.
    """
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        import whisper
        logger.info(f"Loading local Whisper model '{model_name}'...")
        _WHISPER_MODEL = whisper.load_model(model_name)
        logger.info("Whisper model loaded successfully.")
    return _WHISPER_MODEL


def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Step A: Transcribes raw audio bytes using the local Whisper 'base' model.
    Safely writes to a temporary file on Windows and cleans it up after transcription.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        raise ValueError("Audio recording is empty or too short to process.")

    model = load_whisper_model("base")

    # Windows-safe temporary file handling (file must be closed before Whisper opens it)
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_path = temp_file.name
    try:
        temp_file.write(audio_bytes)
        temp_file.flush()
        temp_file.close()

        # fp16=False prevents warnings/crashes when running on Windows CPU
        # initial_prompt conditions Whisper on business & support vocabulary to prevent cutoffs & hallucinations
        result = model.transcribe(
            temp_path,
            fp16=False,
            initial_prompt="Customer support voice recording. Client organization name, urgent complaints, refunds, billing issues, technical failure, account inquiry."
        )
        transcript = result.get("text", "").strip()

        if not transcript:
            raise ValueError("No audible speech could be transcribed from the provided audio.")

        logger.info(f"Transcription successful: {transcript[:80]}...")
        return transcript
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_path}: {e}")


def analyze_transcript_with_gemini(
    transcript: str,
    api_key: Optional[str] = None,
    business_context: Optional[str] = None,
    history_context: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Step B: Analyzes transcript text using Google Gemini with structured output.
    Deeply reasons across business domain context, past historical interactions,
    and active multi-turn conversation memory for unbroken dialogue continuity.
    """
    # Resolve API Key
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not effective_api_key:
        raise ValueError(
            "Google Gemini API key not found. Please set GEMINI_API_KEY in your .env file or enter it in the sidebar."
        )

    # Use google-genai SDK
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=effective_api_key)
    requested_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Upgrade any deprecated model requests (gemini-2.5-flash, gemini-2.0, gemini-1.5)
    if not requested_model or any(requested_model.startswith(p) for p in ["gemini-1.", "gemini-2.", "models/gemini-1.", "models/gemini-2."]):
        logger.info(f"Model '{requested_model}' is deprecated. Upgrading to 'gemini-3.5-flash-lite'.")
        requested_model = "gemini-3.5-flash-lite"

    # Candidate models ordered by priority (handles temporary 503 high-demand or 404s)
    candidate_models = [requested_model]
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        if m not in candidate_models:
            candidate_models.append(m)

    biz_desc = business_context.strip() if business_context else "General Business & Technology Customer Support"
    hist_desc = history_context.strip() if history_context else "No prior interaction history available."

    # Format multi-turn ongoing conversation thread
    conversation_thread_text = ""
    if conversation_history:
        thread_lines = []
        for idx, turn in enumerate(conversation_history, 1):
            user_msg = turn.get("user_transcript") or turn.get("transcript") or ""
            ai_resp = turn.get("drafted_response") or ""
            org_val = turn.get("organization") or ""
            concerns = turn.get("core_concerns") or []
            thread_lines.append(
                f"Turn {idx} [Customer - {org_val}]: \"{user_msg}\"\n"
                f"Turn {idx} [AI Response]: \"{ai_resp}\"\n"
                f"   [Prior Concerns: {', '.join(concerns)}]"
            )
        conversation_thread_text = (
            "=== ACTIVE MULTI-TURN DIALOGUE THREAD (SAME ONGOING CUSTOMER CONVERSATION) ===\n"
            + "\n".join(thread_lines)
            + "\n\nCRITICAL CONVERSATIONAL MEMORY RULE:\n"
            "This incoming voice message is the NEXT TURN in the ongoing conversation thread above with the same customer. "
            "You MUST remember all prior details, references (booking/ticket numbers, earlier explanations, names, requests), "
            "and DO NOT treat this as a brand new isolated customer inquiry. Directly build on the ongoing topic, answer "
            "follow-ups contextually, acknowledge previous statements, and carry forward unresolved demands or issues.\n"
        )

    system_prompt = (
        f"You are the Chief Customer Intelligence & Executive Support AI for: {biz_desc}.\n\n"
        "Your mission is to maintain unbroken conversational continuity and deep contextual awareness. "
        "Understand the FULL CONTEXT of incoming customer voice messages, including short follow-ups, demands, clarifications, or questions.\n\n"
        f"{conversation_thread_text}\n"
        "=== GLOBAL CLIENT HISTORY REFERENCE ===\n"
        f"{hist_desc}\n\n"
        "=== CONTEXT ANALYSIS INSTRUCTIONS ===\n"
        "1. Active Conversation Continuity: If an active dialogue thread exists above, carry over the organization/client identity, "
        "reference numbers, and ongoing topic. If the customer asks 'and what about the refund?' or 'how long will that take?', "
        "connect it immediately to the specific problem discussed in previous turns.\n"
        "2. Organization Identification: Maintain or extract the client/customer identity. If established in prior turns of this dialogue, keep it consistent.\n"
        "3. Core Concerns: List 1 to 4 precise, actionable pain points. Include both new demands from this turn and ongoing core issues from this active dialogue.\n"
        "4. Urgency Classification: Choose strictly 'High' (service outages, financial risks, severe distress, tight deadlines), "
        "'Medium' (operational adjustments, follow-ups, billing questions), or 'Low' (status checks, positive confirmations).\n"
        "5. Drafted Response: Compose an empathetic, polished spoken-style voice response that directly answers the customer's follow-up or statement. "
        "Acknowledge what they previously said, provide concrete answers or reassurance, and maintain an authentic human conversational flow."
    )

    user_prompt = f"Customer Voice Message (Current Turn):\n\"\"\"\n{transcript}\n\"\"\""

    data = None
    last_error = None

    for model_name in candidate_models:
        try:
            logger.info(f"Analyzing transcript using Gemini model: '{model_name}'...")
            response = client.models.generate_content(
                model=model_name,
                contents=[system_prompt, user_prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ConcernAnalysis,
                    temperature=0.2,
                ),
            )
            raw_text = getattr(response, "text", "") or ""
            data = json.loads(raw_text.strip())
            if data:
                break
        except Exception as e:
            logger.warning(f"Model '{model_name}' structured output notice: {e}. Trying prompt fallback...")
            try:
                fallback_prompt = (
                    f"{system_prompt}\n\n"
                    f"{user_prompt}\n\n"
                    "Return ONLY valid JSON matching this schema:\n"
                    "{\n"
                    '  "organization": "string (or Unknown Client)",\n'
                    '  "core_concerns": ["concern 1", "concern 2"],\n'
                    '  "urgency": "Low" | "Medium" | "High",\n'
                    '  "drafted_response": "string"\n'
                    "}"
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=fallback_prompt,
                )
                raw_text = getattr(response, "text", "") or ""
                json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    if data:
                        break
            except Exception as fe:
                last_error = fe
                logger.warning(f"Model '{model_name}' failed completely ({fe}). Checking next candidate model...")
                continue

    if not data:
        raise ValueError(f"Failed to generate analysis with any Gemini model candidates ({candidate_models}). Error: {last_error}")

    # Validate with Pydantic
    validated = ConcernAnalysis(**data)

    # Normalize Urgency field
    urgency_val = validated.urgency.strip().capitalize()
    if urgency_val not in ["Low", "Medium", "High"]:
        urgency_val = "Medium"

    return {
        "organization": validated.organization or "Unknown Client",
        "core_concerns": validated.core_concerns or ["General Inquiry"],
        "urgency": urgency_val,
        "drafted_response": validated.drafted_response.strip(),
    }


def synthesize_speech_gtts(text: str, output_dir: str = "audio_outputs") -> str:
    """
    Step C: Generates a high-quality voice audio file (MP3) from text using gTTS.
    Runs locally and outputs an audio file stored in output_dir.
    """
    from gtts import gTTS

    os.makedirs(output_dir, exist_ok=True)
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]
    filename = f"response_{timestamp_slug}_{unique_id}.mp3"
    file_path = os.path.join(output_dir, filename)

    clean_text = text.strip()
    if not clean_text:
        clean_text = "Thank you for reaching out. We have received your message and will follow up shortly."

    tts = gTTS(text=clean_text, lang="en", slow=False)
    tts.save(file_path)
    logger.info(f"Synthesized voice response saved to {file_path}")
    return file_path


def run_full_pipeline(
    audio_bytes: bytes,
    api_key: Optional[str] = None,
    output_dir: str = "audio_outputs",
) -> Dict[str, Any]:
    """
    Executes the end-to-end multi-stage pipeline:
      1. Whisper Local STT
      2. Gemini Structured Concern Analysis
      3. gTTS Local Voice Synthesis
    Returns a unified dictionary with all analysis attributes and output paths.
    """
    # 1. Transcribe Audio
    transcript = transcribe_audio_bytes(audio_bytes)

    # 2. Analyze with Gemini
    analysis = analyze_transcript_with_gemini(transcript, api_key=api_key)

    # 3. Generate Speech Response
    audio_path = synthesize_speech_gtts(analysis["drafted_response"], output_dir=output_dir)

    return {
        "transcript": transcript,
        "organization": analysis["organization"],
        "urgency": analysis["urgency"],
        "core_concerns": analysis["core_concerns"],
        "drafted_response": analysis["drafted_response"],
        "audio_path": audio_path,
    }

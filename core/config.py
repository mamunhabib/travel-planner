"""
Travel Planner - Configuration and Environment Settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    """
    Application Configuration
    Loads and validates credentials and model hyperparameters.
    """
    # -------------------------------------------------------------------------
    # 1. CORE AI & CREDENTIAL CONFIGURATION
    # -------------------------------------------------------------------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))

    # -------------------------------------------------------------------------
    # 2. AI SECURITY GUARDRAIL CONFIGURATION (Meta Llama Prompt Guard)
    # -------------------------------------------------------------------------
    # WHAT: Pre-inference prompt injection & jailbreak defense settings.
    # WHY:  Protects the generation LLM from adversarial prompt attacks & leaks.
    # MODEL: meta-llama/llama-prompt-guard-2-86m (Executed on Groq LPUs, ~40ms).
    # THRESHOLD: Attack risk score (0.0=benign to 1.0=malicious).
    #            Scores exceeding 0.5 trigger a SECURITY_ALERT and block execution.
    GUARD_MODEL = os.getenv("GUARD_MODEL", "meta-llama/llama-prompt-guard-2-86m")
    GUARD_THRESHOLD = float(os.getenv("GUARD_THRESHOLD", "0.5"))

    @classmethod
    def validate(cls):
        """Validates that critical environment secrets exist."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is missing! Please ensure it is defined in your .env file or Kubernetes Secret."
            )

# Direct exports for convenience
GROQ_API_KEY = Config.GROQ_API_KEY
LLM_MODEL = Config.LLM_MODEL
TEMPERATURE = Config.TEMPERATURE

# -----------------------------------------------------------------------------
# GUARDRAIL DIRECT EXPORTS
# Convenient access for planner.py and other consuming modules
# -----------------------------------------------------------------------------
GUARD_MODEL = Config.GUARD_MODEL
GUARD_THRESHOLD = Config.GUARD_THRESHOLD


"""
Travel Planner - AI Engine & TravelPlanner Workflow Manager
Combines LangChain ChatGroq integration, prompt templating, and session management.
"""
from typing import List, Union
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from core.config import Config
from utils.logger import get_logger
from utils.custom_exception import CustomException

logger = get_logger(__name__)

# System and Human Prompt Template for Day-Trip Itinerary Generation
itinerary_prompt = ChatPromptTemplate([
    (
        "system",
        "You are an expert, helpful travel assistant. Create a structured, engaging day-trip itinerary "
        "for {city} tailored to the user's interests: {interests}.\n"
        "Please format the response using clear markdown:\n"
        "- A brief welcome and city overview\n"
        "- Morning, Afternoon, and Evening breakdown with bulleted recommendations\n"
        "- Practical travel tips (transport, local cuisine, best times to visit)"
    ),
    ("human", "Create a day-trip itinerary for {city} focusing on: {interests}.")
])


# =============================================================================
# [GUARDRAIL COMPONENT] META LLAMA PROMPT GUARD (AI SECURITY LAYER)
# =============================================================================
# WHAT:
#   A dedicated classification model (meta-llama/llama-prompt-guard-2-86m) hosted
#   on Groq Cloud LPUs. It runs pre-flight checks before the generation LLM.
#
# WHY:
#   Prevents prompt injection, jailbreaks, system prompt extraction, and roleplay
#   hijacking without paying the high latency or token cost of large frontier models.
#
# HOW IT WORKS:
#   1. check_prompt_safety() sends user input to Groq's Guard endpoint (~40ms).
#   2. The model returns an attack probability score between 0.0 and 1.0.
#   3. If score > Config.GUARD_THRESHOLD (0.5), GuardrailException is raised.
#   4. A structured 'SECURITY_ALERT' log is emitted for Filebeat -> Logstash -> Elasticsearch.
# =============================================================================

class GuardrailException(Exception):
    """
    [GUARDRAIL EXCEPTION]
    Custom exception raised when user input is classified as an adversarial attack
    or jailbreak attempt by Meta Llama Prompt Guard.
    
    Attributes:
        score (float): The attack probability score returned by the guard model.
        flagged_text (str): The exact input prompt that triggered the security alert.
    """
    def __init__(self, message: str, score: float, flagged_text: str):
        self.score = score
        self.flagged_text = flagged_text
        super().__init__(message)


def check_prompt_safety(text: str) -> float:
    """
    [GUARDRAIL SCREENING FUNCTION]
    Screens input text using Meta Llama Prompt Guard (meta-llama/llama-prompt-guard-2-86m)
    hosted on Groq Cloud LPUs (~40ms latency).
    
    Args:
        text (str): Combined destination and interests string to validate.
        
    Returns:
        float: Attack risk score between 0.0 (safe/benign) and 1.0 (malicious attack).
               Fails open (returns 0.0) on network/API failure to avoid taking down
               the travel planner during transient third-party connection glitches.
    """
    try:
        from groq import Groq
        Config.validate()
        client = Groq(api_key=Config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=Config.GUARD_MODEL,
            messages=[{"role": "user", "content": text}]
        )
        score_str = response.choices[0].message.content.strip()
        return float(score_str)
    except Exception as e:
        logger.warning(f"Guardrail check failed to complete (failing open): {e}")
        return 0.0


# =============================================================================
# [CORE LLM ENGINE] GROQ GENERATION PIPELINE
# =============================================================================

def get_llm() -> ChatGroq:
    """
    Initializes and returns a ChatGroq LLM client instance.
    Validates configuration credentials prior to initialization.
    """
    try:
        Config.validate()
        return ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name=Config.LLM_MODEL,
            temperature=Config.TEMPERATURE,
        )
    except Exception as e:
        logger.error(f"Failed to initialize ChatGroq client: {e}")
        raise CustomException("ChatGroq initialization failed", e)


def generate_itinerary(city: str, interests: Union[List[str], str]) -> str:
    """
    Functional helper to directly generate a travel itinerary for a city and interests.
    Pre-screens inputs with Meta Llama Prompt Guard before invoking the LLM.
    """
    try:
        interests_str = ", ".join(interests) if isinstance(interests, list) else str(interests)
        combined_prompt = f"Destination: {city.strip()} | Interests: {interests_str.strip()}"

        # ---------------------------------------------------------------------
        # [GUARDRAIL CHECKPOINT] Step 1: Pre-Execution Prompt Screening
        # ---------------------------------------------------------------------
        # Intercept and validate inputs with Meta Llama Prompt Guard BEFORE calling
        # the generation LLM. If risk score > GUARD_THRESHOLD (0.50):
        #   1. Emit a structured 'SECURITY_ALERT' log for Filebeat/ELK Stack ingestion.
        #   2. Raise GuardrailException to block execution and prevent token waste.
        # ---------------------------------------------------------------------
        risk_score = check_prompt_safety(combined_prompt)
        if risk_score > Config.GUARD_THRESHOLD:
            logger.warning(
                f"SECURITY_ALERT | Guardrail: Meta-Llama-Guard | Risk_Score: {risk_score:.4f} | "
                f"Blocked_City: '{city.strip()}' | Blocked_Interests: '{interests_str.strip()}'"
            )
            raise GuardrailException(
                f"Security Alert: Your input was flagged as an adversarial prompt injection "
                f"(Threat Score: {risk_score:.2%}). Itinerary generation was blocked.",
                score=risk_score,
                flagged_text=combined_prompt
            )

        # ---------------------------------------------------------------------
        # [LLM INVOCATION] Step 2: Generation LLM (OpenAI GPT-OSS-20B via Groq)
        # Reached ONLY if input successfully clears the guardrail checkpoint above.
        # ---------------------------------------------------------------------
        llm = get_llm()
        messages = itinerary_prompt.format_messages(
            city=city.strip(),
            interests=interests_str.strip()
        )
        response = llm.invoke(messages)
        return str(response.content)
    except GuardrailException:
        # Re-raise GuardrailException so UI can handle security alerts directly
        raise
    except Exception as e:
        logger.error(f"Error generating itinerary for {city}: {e}")
        raise CustomException(f"Failed to generate itinerary for {city}", e)


# Backward-compatibility alias for tutorial spelling
generate_itineary = generate_itinerary


class TravelPlanner:
    """
    Stateful workflow manager for the Travel Planner application.
    Encapsulates user session inputs, message history, logging, and LLM calls.
    """
    def __init__(self):
        self.messages: List[BaseMessage] = []
        self.city: str = ""
        self.interests: List[str] = []
        self.itinerary: str = ""
        self.itineary: str = ""  # Compatibility alias
        logger.info("Initialized new TravelPlanner instance")

    def set_city(self, city: str):
        """Sets destination city and appends to message log."""
        try:
            if not city or not city.strip():
                raise ValueError("City name cannot be empty")
            self.city = city.strip()
            self.messages.append(HumanMessage(content=f"Destination: {self.city}"))
            logger.info(f"City set successfully: '{self.city}'")
        except Exception as e:
            logger.error(f"Error while setting city: {e}")
            raise CustomException("Failed to set city", e)

    def set_interests(self, interests_str: str):
        """Parses comma-separated interests and appends to message log."""
        try:
            if not interests_str or not interests_str.strip():
                raise ValueError("Interests cannot be empty")
            self.interests = [i.strip() for i in interests_str.split(",") if i.strip()]
            self.messages.append(HumanMessage(content=f"Interests: {interests_str.strip()}"))
            logger.info(f"Interests set successfully: {self.interests}")
        except Exception as e:
            logger.error(f"Error while setting interests: {e}")
            raise CustomException("Failed to set interests", e)

    def create_itinerary(self) -> str:
        """Invokes Groq LLM to generate the itinerary and stores result in history."""
        try:
            if not self.city:
                raise ValueError("City has not been set. Call set_city() first.")
            if not self.interests:
                raise ValueError("Interests have not been set. Call set_interests() first.")

            logger.info(f"Generating itinerary for '{self.city}' with interests: {self.interests}")
            itinerary_content = generate_itinerary(self.city, self.interests)
            
            self.itinerary = itinerary_content
            self.itineary = itinerary_content  # Compatibility alias
            self.messages.append(AIMessage(content=itinerary_content))

            logger.info(f"Itinerary generated successfully for '{self.city}' ({len(itinerary_content)} chars)")
            return self.itinerary
        except GuardrailException:
            # [GUARDRAIL PROPAGATION]
            # Re-raise GuardrailException directly so app/ui.py can intercept it
            # and render a prominent red security warning banner to the user.
            raise
        except Exception as e:
            logger.error(f"Error while creating itinerary for '{self.city}': {e}")
            raise CustomException("Failed to create itinerary", e)

    # Backward-compatibility alias for tutorial spelling
    create_itineary = create_itinerary

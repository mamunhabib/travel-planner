"""
Travel Planner - Streamlit UI Layout and Frontend
Provides an interactive web interface for generating day-trip itineraries with Groq LLM.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path so 'core' and 'utils' are resolvable anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
# [GUARDRAIL INTEGRATION]
# Import GuardrailException to catch and gracefully display adversarial prompt blocks
from core.planner import TravelPlanner, GuardrailException
from utils.logger import get_logger
from utils.custom_exception import CustomException

logger = get_logger("travel_planner.ui")

# 1. Page Configuration
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished aesthetics
st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #4B5563;
            margin-bottom: 1.5rem;
        }
        .itinerary-box {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 24px;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)


def set_preset(city: str, interests: str):
    """Callback to update session state when a preset button is clicked."""
    st.session_state["city_input"] = city
    st.session_state["interests_input"] = interests


def main():
    # Initialize session state variables
    if "city_input" not in st.session_state:
        st.session_state["city_input"] = ""
    if "interests_input" not in st.session_state:
        st.session_state["interests_input"] = ""
    if "itinerary" not in st.session_state:
        st.session_state["itinerary"] = ""
    if "last_city" not in st.session_state:
        st.session_state["last_city"] = ""

    # 2. Sidebar Configuration
    with st.sidebar:
        st.header("✈️ Travel Planner AI")
        st.markdown(
            "An intelligent day-trip itinerary planner powered by **Groq Cloud LPUs** "
            "and observable via **Centralized ELK Logging**."
        )
        st.divider()
        
        st.subheader("💡 Quick Examples")
        st.caption("Click a preset below to populate sample destinations:")
        
        st.button(
            "🇯🇵 Kyoto (Tea & Zen)",
            on_click=set_preset,
            args=("Kyoto", "Tea ceremony, Zen gardens, bamboo groves, matcha sweets"),
            use_container_width=True
        )
        st.button(
            "🇫🇷 Paris (Art & Pastries)",
            on_click=set_preset,
            args=("Paris", "Impressionist art museums, croissant bakeries, historic bridges, evening jazz"),
            use_container_width=True
        )
        st.button(
            "🇺🇸 New York (Culture & Food)",
            on_click=set_preset,
            args=("New York", "Central Park stroll, Broadway architecture, skyline views, street pizza"),
            use_container_width=True
        )
        
        st.divider()
        st.caption("Engine: `openai/gpt-oss-20b` via Groq")
        # [GUARDRAIL METADATA] Display the active real-time security pre-filter
        st.caption("🛡️ Security Guardrail: `meta-llama/llama-prompt-guard-2-86m`")
        st.caption("Centralized Logging: Filebeat ➡️ Logstash ➡️ Elasticsearch")

    # 3. Main Header
    st.markdown('<div class="main-header">🌍 AI Travel Itinerary Planner</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Craft a personalized day-trip itinerary tailored to your passions in seconds.</div>',
        unsafe_allow_html=True
    )

    # 4. User Input Form
    with st.form("travel_form"):
        col1, col2 = st.columns([1, 1])
        with col1:
            city_val = st.text_input(
                "🏙️ Destination City",
                value=st.session_state["city_input"],
                placeholder="e.g., Tokyo, Rome, Barcelona, Vancouver"
            )
        with col2:
            interests_val = st.text_input(
                "🎨 Your Interests & Preferences",
                value=st.session_state["interests_input"],
                placeholder="e.g., Historical architecture, local street food, photography"
            )

        submit_btn = st.form_submit_button("✨ Generate Itinerary", use_container_width=True)

    # 5. Form Submission Handling
    if submit_btn:
        city = city_val.strip()
        interests = interests_val.strip()

        # Update session state with submitted values
        st.session_state["city_input"] = city
        st.session_state["interests_input"] = interests

        if not city or not interests:
            st.warning("⚠️ Please provide both a **Destination City** and your **Interests** to generate a plan.")
            logger.warning("User submitted incomplete form (missing city or interests).")
        else:
            logger.info(f"UI form submitted for destination: '{city}', interests: '{interests}'")
            try:
                with st.spinner(f"🧭 Consulting AI travel guide for {city}..."):
                    planner = TravelPlanner()
                    planner.set_city(city)
                    planner.set_interests(interests)
                    itinerary = planner.create_itinerary()

                st.session_state["itinerary"] = itinerary
                st.session_state["last_city"] = city
                st.success("🎉 Your personalized itinerary is ready!")
            # =================================================================
            # [GUARDRAIL INTERCEPTION & USER FEEDBACK]
            # WHAT: Catches GuardrailException raised by Meta Llama Prompt Guard.
            # WHY:  Adversarial prompts (jailbreaks, system prompt leaks) are
            #       blocked before reaching the generation LLM, saving tokens.
            # UI:   Clears output and renders a prominent red security alert
            #       with the threat score and guidance for the user.
            # =================================================================
            except GuardrailException as ge:
                st.session_state["itinerary"] = ""
                st.error(f"🛡️ **Security Guardrail Blocked**: {ge}")
                st.info("💡 **Notice:** Your query was flagged by Meta Llama Prompt Guard as a potential adversarial injection. Please submit standard travel and tourism requests.")
                logger.warning(f"UI caught GuardrailException: {ge}")
            except CustomException as ce:
                st.error(f"❌ Failed to generate itinerary: {ce}")
                logger.error(f"UI caught CustomException: {ce}")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")
                logger.error(f"UI caught unexpected error: {e}")

    # 6. Display Persisted Itinerary
    if st.session_state.get("itinerary"):
        with st.container():
            st.markdown("### 📄 Your Personalized Day-Trip Itinerary")
            st.markdown(st.session_state["itinerary"])
            
            st.download_button(
                label="📥 Download Itinerary (Markdown)",
                data=st.session_state["itinerary"],
                file_name=f"{st.session_state.get('last_city', 'travel').lower()}_day_trip_itinerary.md",
                mime="text/markdown",
                use_container_width=True
            )


if __name__ == "__main__":
    main()

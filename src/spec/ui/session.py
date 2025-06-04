import streamlit as st

from spec.models import SingletonMeta
from spec.ui.authen import Authenticator
from spec.utils.captcha import Captcha


@st.cache_resource
def get_blocked_users():
    return {}

class SessionManager(metaclass=SingletonMeta):
    """Manages Streamlit session state."""

    def __init__(self, authenticator: Authenticator):        
        state = st.session_state
        state.setdefault("messages", [])
        state.setdefault("previous_response_id", None)
        state.setdefault("captcha_code", Captcha().generate_captcha_code())
        state.setdefault("blocked_users", get_blocked_users())
        state.setdefault("username", authenticator.username())
        
    def reset_conversation(self):
        """Resets conversation state."""

        st.session_state["messages"] = []
        st.session_state['previous_response_id'] = None

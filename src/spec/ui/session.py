import uuid

import httpx
import streamlit as st

from spec.config import settings
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
        state.setdefault("session_id", str(uuid.uuid4()))
        state.setdefault("captcha_code", Captcha().generate_captcha_code())
        state.setdefault("blocked_users", get_blocked_users())
        state.setdefault("username", authenticator.username())
        
    def reset_conversation(self):
        """Resets conversation state."""

        st.session_state["messages"] = []
        st.session_state['session_id'] = str(uuid.uuid4())
        
        try:
            httpx.post(f"{settings.url}/new_chat", json={"session_id": st.session_state.session_id}, timeout=5)
        except httpx.HTTPError as e:
            st.sidebar.error(f"Backend error: {e}")

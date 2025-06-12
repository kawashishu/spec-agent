from datetime import datetime

import streamlit as st

from spec.ui.authen import Authenticator, Captcha


@st.cache_resource
def get_blocked_users():
    return {}

class SessionManager():
    """Manages Streamlit session state."""

    def __init__(self, authenticator: Authenticator):        
        state = st.session_state
        state.setdefault("ui_messages", [])
        state.setdefault("agent_messages", [])
        state.setdefault("captcha_code", Captcha().generate_captcha_code())
        state.setdefault("blocked_users", get_blocked_users())
        state.setdefault("username", authenticator.username())
        state.setdefault("init_time", datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        
    def reset_conversation(self):
        """Resets conversation state."""

        st.session_state["ui_messages"] = []
        st.session_state['agent_messages'] = []
        st.session_state["init_time"] = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
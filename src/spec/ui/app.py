# streamlit_frontend.py
import base64
import io
import json

import httpx
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from PIL import Image

from spec.config import settings

from .authen import Authenticator
from .session import SessionManager


class UI:
    """Manages UI components."""
    def __init__(self, authenticator: Authenticator, session: SessionManager):
        self.authenticator = authenticator
        self.session = session

    @staticmethod
    def switch_state(key, value):
        st.session_state[key] = value

    def render_new_chat(self):
        st.button("New Chat", on_click=self.session.reset_conversation)
        st.sidebar.markdown("---")

    def render(self):
        # Render the sidebar
        with st.sidebar:
            col1, col2 = st.sidebar.columns([4, 1])
            with col2:
                if st.button('↪'):
                    self.authenticator.logout()

            with col1:
                st.markdown(f"""
                <div style="margin-left: 5px; padding: 5px;">
                    <strong>User: {st.session_state['username']}</strong>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            self.render_new_chat()

        # Render the history
        # ─── Display history ────────────────────────────────────────────────────────
        for res in st.session_state.messages:
            try:
                with st.chat_message(res["role"]):
                    if isinstance(res["content"], str):
                        st.write(res["content"])
                    elif isinstance(res["content"], list):
                        for c in res["content"]:
                            if isinstance(c, str):
                                st.write(c)
                            elif isinstance(c, pd.DataFrame):
                                st.dataframe(c)
                            elif isinstance(c, Image.Image):
                                st.image(c)
                            elif isinstance(c, Figure):
                                st.pyplot(c)
            except Exception as e:
                continue

      
def render_stream(prompt: str):
    # Define list of allowed agents that can stream
    
    body = {"session_id": st.session_state.session_id, "prompt": prompt, "username": st.session_state.username}

    with httpx.stream("POST", f"{settings.url}/chat", json=body, timeout=None) as r:
        for raw in r.iter_lines():  
            if not raw:
                continue
            
            msg = json.loads(raw)
            kind = msg.get("kind")
                        
            if kind == "text":
                yield msg["data"]
            elif kind == "dataframe":
                df = pd.DataFrame(**msg["data"])
                yield df
            elif kind.startswith("image/"):
                bytes = base64.b64decode(msg["b64"])
                img = Image.open(io.BytesIO(bytes))
                yield img
            elif kind == "end_stream":
                break
            
class App:
    """Main chat application."""

    def __init__(self, max_login_attempts: int = 5, max_waiting_time: int = 10):
        self.authenticator = Authenticator(max_login_attempts, max_waiting_time)
        self.session = SessionManager(self.authenticator)
        self.ui = UI(self.authenticator, self.session)
    
    def query(self, prompt: str):
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        responses = st.chat_message("assistant").write_stream(render_stream(prompt))
        
        st.session_state.messages.append({"role": "assistant", "content": responses})
        
    def run(self):
        
        if not self.authenticator.is_authenticated():
            self.authenticator.show_login_screen()
            st.stop()

        # Main chat UI
        self.ui.render()
        
        if user_input := st.chat_input("Type your query..."):
            self.query(user_input)

if __name__ == "__main__":
    App().run()

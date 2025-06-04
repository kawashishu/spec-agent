# streamlit_frontend.py
import asyncio
import threading

import pandas as pd
import streamlit as st
from agents import Agent, Runner
from matplotlib.figure import Figure
from openai.types.responses import ResponseTextDeltaEvent
from PIL import Image

from spec.agents import triage_agent
from spec.config import *
from spec.models import ContextHook, LiveStream
from spec.ui.authen import Authenticator
from spec.ui.session import SessionManager


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


def run_agent_stream(agent: Agent, input: str, previous_response_id: str, buffer: LiveStream, hook: ContextHook):
        async def _runner():
            result = Runner.run_streamed(agent, input=input, previous_response_id=previous_response_id, context=hook)
            
            async for ev in result.stream_events():
                if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                    buffer.write(ev.data.delta)
            buffer.finish()
            
            st.session_state.previous_response_id = result.last_response_id
        
        asyncio.run(_runner())

class App:
    """Main chat application."""

    def __init__(self, max_login_attempts: int = 5, max_waiting_time: int = 10):
        self.authenticator = Authenticator(max_login_attempts, max_waiting_time)
        self.session = SessionManager(self.authenticator)
        self.ui = UI(self.authenticator, self.session)

    
    def query(self, prompt: str):
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        buffer = LiveStream()
        context_hook = ContextHook(buffer)
        
        previous_response_id = st.session_state.previous_response_id
        threading.Thread(target=run_agent_stream, args=(triage_agent, prompt, previous_response_id, buffer, context_hook), daemon=True).start()

        with st.chat_message("assistant"):
            response = st.write_stream(buffer.stream())
        st.session_state.messages.append({"role": "assistant", "content": response})
        
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

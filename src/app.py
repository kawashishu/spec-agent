# streamlit_frontend.py
import base64
import io
import json
import time
import uuid
from datetime import datetime, timedelta
# BytesIO
from io import BytesIO
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
import yaml
from argon2 import PasswordHasher
from matplotlib.figure import Figure

st.set_page_config(layout="wide")
from PIL import Image
from streamlit_cookies_manager import EncryptedCookieManager
from yaml.loader import SafeLoader

from schema import SingletonMeta
from settings.constraints import *
from utils.captcha import Captcha

API_URL = "http://127.0.0.1:9000"

class Authenticator(metaclass=SingletonMeta):
    def __init__(self, max_login_attempts: int = 5, max_waiting_time: int = 10):
        self.cookies = EncryptedCookieManager(prefix='APO', password='APO_Pwd')
        if not self.cookies.ready():
            st.stop()

        self.max_login_attempts = max_login_attempts
        self.max_waiting_time = max_waiting_time

    def is_authenticated(self) -> bool:
        return self.cookies.get('is_authenticated', '0') == '1'

    def username(self) -> str:
        return self.cookies.get('name', 'unknown')

    def logout(self):
        """Logout and rerun the app."""
        self.cookies['is_authenticated'] = '0'
        self.cookies['name'] = ''
        self.cookies['email'] = ''
        self.cookies.save()
        st.rerun()

    def show_login_screen(self):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.write("")
        with col2:
            login_form = st.form(key='Login', clear_on_submit=True)
            login_form.subheader('Login')

            email = login_form.text_input('Email')
            password = login_form.text_input('Password', type='password')

            # Generate captcha and display
            captcha_code = st.session_state['captcha_code']
            captcha_image = Captcha.generate_captcha_image(captcha_code)
            captcha_base64 = Captcha.image_to_base64(captcha_image)
            st.image(BytesIO(base64.b64decode(captcha_base64)), caption='Captcha')
            captcha_input = login_form.text_input("Enter Captcha")

            submitted = login_form.form_submit_button('Login')
            if submitted:
                # Initialize user_data if email is not in the list
                if email not in st.session_state['blocked_users']:
                    st.session_state['blocked_users'][email] = {
                        "attempts": 0,
                        "blocked": False,
                        "locked_time": None
                    }
                user_data = st.session_state['blocked_users'][email]

                # Check if the user is locked
                if user_data["blocked"]:
                    locked_time = user_data["locked_time"]
                    if locked_time:
                        time_elapsed = datetime.now() - locked_time
                        if time_elapsed > timedelta(minutes=self.max_waiting_time):
                            # Time out => unlock the account
                            st.session_state['blocked_users'][email] = {
                                "attempts": 0,
                                "blocked": False,
                                "locked_time": None
                            }
                            st.info("Account has been unlocked. Please login again.")
                        else:
                            remain = timedelta(minutes=self.max_waiting_time) - time_elapsed
                            st.error(
                                f"""You've exceeded the maximum number of login attempts ({self.max_login_attempts}). 
                                For security reasons, your account has been temporarily locked. 
                                Please wait for ~{int(remain.total_seconds()//60)} minutes and try again.
                                """
                            )
                            st.stop()

                if captcha_input != captcha_code:
                    user_data["attempts"] += 1
                    st.error("Incorrect Captcha. Please try again.")
                else:
                    login_message = self.authenticate(email, password)
                    if login_message == 'OK':
                        # Reset the number of attempts
                        st.session_state['blocked_users'][email] = {
                            "attempts": 0,
                            "blocked": False,
                            "locked_time": None
                        }
                        st.session_state['username'] = self.username()
                        st.session_state['email'] = email
                        st.rerun()
                    else:
                        user_data["attempts"] += 1
                        st.error(login_message)

                # If the number of attempts exceeds the allowed limit => lock the user
                if user_data["attempts"] >= self.max_login_attempts:
                    user_data["blocked"] = True
                    user_data["locked_time"] = datetime.now()
                    remain = timedelta(minutes=self.max_waiting_time) - time_elapsed
                    st.error(
                        f"""You've exceeded the maximum number of login attempts ({self.max_login_attempts}). 
                            For security reasons, your account has been temporarily locked. 
                            Please wait for ~{int(remain.total_seconds()//60)} minutes and try again.
                            """
                    )
        with col3:
            st.write("")

    def authenticate(self, email, password):
        with open(AUTHEN_FILE, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
        ph = PasswordHasher()

        if email in config:
            try:
                ph.verify(config[email]['password'], password)
                self.cookies['is_authenticated'] = '1'
                self.cookies['name'] = config[email]['name']
                self.cookies['email'] = email
                self.cookies.save()
                return "OK"
            except Exception:
                return "Email/Password is incorrect!"
        else:
            return "This email is not yet registered!"

######################################################################
# Session Manager
######################################################################
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
            httpx.post(f"{API_URL}/new_chat", json={"session_id": st.session_state.session_id}, timeout=5)
        except httpx.HTTPError as e:
            st.sidebar.error(f"Backend error: {e}")

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

    with httpx.stream("POST", f"{API_URL}/chat", json=body, timeout=None) as r:
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

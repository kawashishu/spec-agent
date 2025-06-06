
# streamlit_frontend.py
import base64
import time
from datetime import datetime, timedelta
# BytesIO
from io import BytesIO

import streamlit as st
import yaml
from argon2 import PasswordHasher
from streamlit_cookies_manager import EncryptedCookieManager
from yaml.loader import SafeLoader

from spec.config import settings
from spec.models import SingletonMeta
from spec.utils.captcha import Captcha


class Authenticator():
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
        if 'captcha_code' not in st.session_state:
            st.session_state['captcha_code'] = Captcha().generate_captcha_code()

        if 'blocked_users' not in st.session_state:
            st.session_state['blocked_users'] = {}
            
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
                    st.session_state['captcha_code'] = Captcha().generate_captcha_code()
                    time.sleep(3)
                    st.rerun()
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
        with open(settings.authen_file, 'r', encoding='utf-8') as file:
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
import streamlit as st
import random
import string
from captcha.image import ImageCaptcha
from io import BytesIO
import base64

class Captcha:
    
    @classmethod
    def generate_captcha_code(cls, length=5):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @classmethod
    def generate_captcha_image(cls, captcha_text):
        image = ImageCaptcha()
        data = image.generate(captcha_text)
        return data.getvalue()
    
    @classmethod
    def image_to_base64(cls, img_data):
        return base64.b64encode(img_data).decode()
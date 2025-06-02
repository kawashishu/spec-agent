##############################################
##############################################
# Generate authen.yaml with argon2-cffi==23.1.0
# The version of the lib is important, otherwise it might lead to a password failure
import secrets
import string

import yaml
from argon2 import PasswordHasher


def generate_secure_password(length=16):
    if length < 4:
        raise ValueError("Password length should be at least 4 to include all character types")

    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    punctuation = string.punctuation

    # Ensure the password includes at least one of each type
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(punctuation)
    ]

    # Fill the rest of the password length with random choices from the combined set
    combined_set = lowercase + uppercase + digits + punctuation
    password += [secrets.choice(combined_set) for _ in range(length - 4)]

    # Shuffle the list to mix up the order of characters
    secrets.SystemRandom().shuffle(password)

    # Convert the list to a string
    return ''.join(password)

ph = PasswordHasher()
data = {
 'v.quynhnn25@vinit.tech': {'name': 'Nguyen Ngoc Quynh'},
 'v.namhnq1@vinit.tech': {'name': 'Ho Nguyen Quoc Nam'},
 'v.phuongnh52@vinit.tech': {'name': 'Nguyen Huu Phuong'},
 'v.DIR.IT3@vinfast.vn': {'name': 'Vu Ngoc Trong'},
 }

# gen hashed password
for email in data.keys():
    name = data[email]['name']
    password = generate_secure_password(16)
    hashed_password = ph.hash(password)
    print(f'{email}:')
    print(f'name:{name}')
    print(f'hashed password:{hashed_password}')
    print(f'raw password: {password}')
    data[email]['password'] = hashed_password
    data[email]['raw_password'] = password

with open('authen.yaml', 'w') as file:
    yaml.dump(data, file, default_flow_style=False)


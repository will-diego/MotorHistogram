# Motor Data Dashboard Configuration
# This file contains sensitive authentication data
# Do NOT commit this file to version control!

import os

# Try to import Streamlit secrets (for Streamlit Cloud)
try:
    import streamlit as st  # type: ignore
    # Get secrets from Streamlit Cloud
    def get_secret(section: str, key: str, default: str) -> str:
        try:
            return st.secrets[section][key]
        except:
            return os.getenv(f"{section.upper()}_{key}", default)
    
    # Authentication credentials from Streamlit secrets or environment variables
    AUTH_USERS = {
        # Username: password_hash
        "will": get_secret("passwords", "WILL_PASSWORD_HASH", "832816e4cdf8e0501116098ef850deb1a42bf3cbdc07af319086c4439b14c407"),
        "bimotal": get_secret("passwords", "BIMOTAL_PASSWORD_HASH", "e4f009916270bff8106f9bbd562d1937e4fdb92b1df2ad570458767e8051d71e")
    }
    
    # PostHog API Configuration
    POSTHOG_API_KEY = get_secret("api", "POSTHOG_API_KEY", "phx_ETiyf25aQLPtOPBBnPHYi6vJCPvKOtalYtaAWIZ1XhvNs6n")
    POSTHOG_PROJECT_ID = get_secret("api", "POSTHOG_PROJECT_ID", "113002")

except ImportError:
    # Fallback for non-Streamlit environments
    AUTH_USERS = {
        "will": os.getenv("PASSWORDS_WILL_PASSWORD_HASH", "832816e4cdf8e0501116098ef850deb1a42bf3cbdc07af319086c4439b14c407") or "832816e4cdf8e0501116098ef850deb1a42bf3cbdc07af319086c4439b14c407",
        "bimotal": os.getenv("PASSWORDS_BIMOTAL_PASSWORD_HASH", "e4f009916270bff8106f9bbd562d1937e4fdb92b1df2ad570458767e8051d71e") or "e4f009916270bff8106f9bbd562d1937e4fdb92b1df2ad570458767e8051d71e"
    }
    POSTHOG_API_KEY = os.getenv("API_POSTHOG_API_KEY", "phx_ETiyf25aQLPtOPBBnPHYi6vJCPvKOtalYtaAWIZ1XhvNs6n") or "phx_ETiyf25aQLPtOPBBnPHYi6vJCPvKOtalYtaAWIZ1XhvNs6n"
    POSTHOG_PROJECT_ID = os.getenv("API_POSTHOG_PROJECT_ID", "113002") or "113002"

# Set environment variables for the scripts to use
os.environ.setdefault("POSTHOG_API_KEY", POSTHOG_API_KEY)
os.environ.setdefault("POSTHOG_PROJECT_ID", POSTHOG_PROJECT_ID)

# Password utility function
def hash_new_password(password):
    """Utility function to generate password hash for new users"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

# Example usage:
# print(f"Hash for 'mypassword': {hash_new_password('mypassword')}") 
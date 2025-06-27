import streamlit as st

st.title("🧪 Simple Test App")
st.write("If you can see this, basic Streamlit is working!")

# Test imports
try:
    import pandas as pd
    st.success("✅ Pandas imported successfully")
except Exception as e:
    st.error(f"❌ Pandas import failed: {e}")

try:
    import matplotlib.pyplot as plt
    st.success("✅ Matplotlib imported successfully")
except Exception as e:
    st.error(f"❌ Matplotlib import failed: {e}")

try:
    import requests
    st.success("✅ Requests imported successfully")
except Exception as e:
    st.error(f"❌ Requests import failed: {e}")

try:
    from config import AUTH_USERS
    st.success("✅ Config imported successfully")
    st.write(f"Found {len(AUTH_USERS)} users in config")
except Exception as e:
    st.error(f"❌ Config import failed: {e}")

st.write("Test completed!") 
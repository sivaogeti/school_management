# openai_client.py (or anywhere you like)

import os
from typing import Optional

try:
    import streamlit as st
except Exception:  # running outside Streamlit
    st = None

from openai import OpenAI


def _get_secret(key: str) -> Optional[str]:
    """
    Safely read a key from st.secrets if Streamlit is present; otherwise None.
    """
    if st is None:
        return None
    try:
        return st.secrets[key]  # handles flat keys like "OPENAI_API_KEY"
    except Exception:
        return None


def _get_nested_secret(section: str, key: str) -> Optional[str]:
    """
    Safely read a nested key like st.secrets["api_keys"]["openai_api_key"].
    """
    if st is None:
        return None
    try:
        section_dict = st.secrets.get(section, None)
        if isinstance(section_dict, dict):
            return section_dict.get(key)
    except Exception:
        pass
    return None


def _resolve_openai_key() -> Optional[str]:
    """
    Resolution order:
    1) st.secrets["api_keys"]["openai_api_key"]     (your current style)
    2) st.secrets["openai_api_key"]                 (flat, lowercase)
    3) st.secrets["OPENAI_API_KEY"]                 (flat, uppercase standard)
    4) os.environ["OPENAI_API_KEY"]                 (env var)
    """
    # 1) nested section
    key = _get_nested_secret("api_keys", "openai_api_key")
    if key:
        return key

    # 2) flat, lowercase
    key = _get_secret("openai_api_key")
    if key:
        return key

    # 3) flat, uppercase
    key = _get_secret("OPENAI_API_KEY")
    if key:
        return key

    # 4) environment variable
    return os.getenv("OPENAI_API_KEY")


# Cache the client in Streamlit so we don’t recreate it
if st is not None:
    @st.cache_resource(show_spinner=False)
    def make_openai_client() -> OpenAI:
        api_key = _resolve_openai_key()
        if not api_key:
            if st is not None:
                # Show a friendly, non-leaky error
                present_top = list(st.secrets.keys()) if hasattr(st, "secrets") else []
                present_api_keys = []
                try:
                    if isinstance(st.secrets.get("api_keys", None), dict):
                        present_api_keys = list(st.secrets["api_keys"].keys())
                except Exception:
                    pass
                st.error(
                    "OpenAI API key not found. Please set one of the following:\n"
                    "- st.secrets['api_keys']['openai_api_key']\n"
                    "- st.secrets['openai_api_key']\n"
                    "- st.secrets['OPENAI_API_KEY']\n"
                    "- or environment variable OPENAI_API_KEY"
                )
                st.caption(f"Top-level secrets present: {present_top}")
                if present_api_keys:
                    st.caption(f"[api_keys] entries present: {present_api_keys}")
                st.stop()
            # If somehow outside Streamlit and missing key, raise
            raise RuntimeError("Missing OpenAI API key (set OPENAI_API_KEY).")
        return OpenAI(api_key=api_key)
else:
    # Non-Streamlit fallback (e.g., tests, scripts)
    def make_openai_client() -> OpenAI:
        api_key = _resolve_openai_key()
        if not api_key:
            raise RuntimeError("Missing OpenAI API key (set OPENAI_API_KEY).")
        return OpenAI(api_key=api_key)

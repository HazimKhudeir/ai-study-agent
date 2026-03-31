"""
Compatibility shim: the canonical Streamlit app lives in ``app.py``.

Use::

    streamlit run app.py
"""

from app import main as run

if __name__ == "__main__":
    run()

import sys
import os

# خلي Python يشوف الفولدر الرئيسي
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import main as run

if __name__ == "__main__":
    run()

from pathlib import Path
import sys

PRODUCT='Oasis Attend'
PRODUCT_AR='حضور أوايسس'
OWNER='Oasis Digital Solutions'
ACCENT='#D39340'  # Reserved brand colour; UI restyling remains deferred.

def brand_asset(name):
    return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'brand'/name

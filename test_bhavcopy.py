import sys
from datetime import date
from src.data.nse_bhavcopy import _download_bhavcopy, _parse_bhavcopy, last_trading_day
import zipfile
import io
import pandas as pd

d = last_trading_day(0)
z = _download_bhavcopy(d)
if z:
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        csv_name = next((n for n in zf.namelist() if n.endswith(".csv")), None)
        with zf.open(csv_name) as f:
            df = pd.read_csv(f, low_memory=False)
            print("Raw columns:", df.columns.tolist())

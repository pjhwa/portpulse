# utils.py

def normalize_adjclose(df):
    df.columns = [col.lower() for col in df.columns]
    if "adjclose" not in df.columns:
        if "adj close" in df.columns:
            df["adjclose"] = df["adj close"]
        elif "close" in df.columns:
            df["adjclose"] = df["close"]
        else:
            raise ValueError("Cannot find a suitable column to set as 'adjclose'")

    if "close" not in df.columns and "adjclose" in df.columns:
        df["close"] = df["adjclose"]
    return df

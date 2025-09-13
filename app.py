import streamlit as st
import pandas as pd
from io import BytesIO

st.title("CSV/Excel Compiler - Preserve EncounterID")

uploaded_files = st.file_uploader(
    "Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True
)

def read_csv_strict(file):
    """Read CSV as strings, clean formulas/quotes, handle bad lines"""
    df = pd.read_csv(
        file,
        dtype=str,
        keep_default_na=False,
        quotechar='"',
        on_bad_lines='skip',
        encoding='utf-8'
    )
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    return df

def read_file(file):
    if file.name.endswith(".csv"):
        return read_csv_strict(file)
    else:
        return pd.read_excel(file, dtype=str)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        dfs.append(read_file(file))

    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(inplace=True)

    st.subheader("Compiled Data (EncounterID preserved)")
    st.dataframe(compiled_df.astype(str), width='stretch')

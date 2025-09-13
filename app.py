import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Day Start/End Compiler", layout="wide")
st.title("📊 CSV/Excel Compiler with EncounterID Fix")

# File uploader
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True
)

def csv_to_excel(file):
    """Convert CSV to Excel in-memory, clean it, and preserve EncounterID."""
    df = pd.read_csv(
        file, dtype=str, keep_default_na=False, quotechar='"', encoding='utf-8', on_bad_lines='skip'
    )
    # Remove formulas and extra quotes
    for col in df.columns:
        df[col] = df[col].str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    # Save to Excel in memory
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output, df

def get_level(balance):
    try:
        b = float(balance)
        if b <= 249.99: return "Level1"
        elif b <= 1999.99: return "Level2"
        elif b <= 9999.99: return "Level3"
        elif b <= 24999.99: return "Level4"
        else: return "Level5"
    except:
        return None

def to_excel_bytes(df):
    out = BytesIO()
    df.to_excel(out, index=False)
    out.seek(0)
    return out

if uploaded_files:
    compiled_dfs = []
    excel_files_bytes = []

    for file in uploaded_files:
        if file.name.endswith(".csv"):
            excel_io, df = csv_to_excel(file)
            excel_files_bytes.append((file.name.replace(".csv",".xlsx"), excel_io))
        else:
            df = pd.read_excel(file, dtype=str)
        compiled_dfs.append(df)

    # Combine all DataFrames
    compiled_df = pd.concat(compiled_dfs, ignore_index=True)
    compiled_df.drop_duplicates(inplace=True)

    # Convert Balance (F column) to numeric for Level calculation
    balance_col = compiled_df.columns[5]  # F column
    compiled_df[balance_col] = pd.to_numeric(compiled_df[balance_col].str.replace(',', '', regex=False), errors='coerce')

    # Apply Level calculation (store in column T)
    compiled_df["Level"] = compiled_df[balance_col].apply(get_level)

    # Sort by Balance descending and reset index
    compiled_df.sort_values(by=balance_col, ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    st.subheader("Compiled Data (EncounterID preserved)")
    st.dataframe(compiled_df.astype(str), width='stretch')

    # Download compiled Excel
    st.download_button(
        "⬇️ Download Compiled Excel",
        data=to_excel_bytes(compiled_df),
        file_name="compiled.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Optional: Download individually converted CSV → Excel files
    st.subheader("Converted CSV → Excel Files")
    for fname, excel_io in excel_files_bytes:
        st.download_button(
            f"⬇️ {fname}",
            data=excel_io,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

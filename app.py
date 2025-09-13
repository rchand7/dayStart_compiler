import streamlit as st
import pandas as pd
from io import BytesIO

st.title("CSV → Excel Compiler")

# Upload files (CSV or Excel)
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv","xlsx"],
    accept_multiple_files=True
)

excel_buffers = []

if uploaded_files:
    for file in uploaded_files:
        try:
            if file.name.endswith(".csv"):
                # Read CSV robustly
                df = pd.read_csv(file, dtype=str, on_bad_lines='skip', engine='python')
            else:
                df = pd.read_excel(file, dtype=str)

            # Clean strings
            for col in df.select_dtypes(include='object').columns:
                df[col] = df[col].str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()

            # Save to in-memory Excel
            buffer = BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            excel_buffers.append(buffer)
        except Exception as e:
            st.error(f"Failed to process {file.name}: {e}")

# Compile all Excel files
if excel_buffers:
    dfs = [pd.read_excel(buf, dtype=str) for buf in excel_buffers]
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure columns exist
    for col in ["EncounterID","FacilityCode","Balance","Age","CurrentPayer"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Convert numeric columns
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Apply Level calculation
    def get_level(val):
        if pd.isna(val): return None
        val = float(val)
        if val <= 249.99: return "Level1"
        elif val <= 1999.99: return "Level2"
        elif val <= 9999.99: return "Level3"
        elif val <= 24999.99: return "Level4"
        else: return "Level5"

    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age > 0
    compiled_df = compiled_df[compiled_df["Age"] > 0]

    # Sort by Balance descending
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    st.subheader("Compiled Data")
    st.dataframe(compiled_df)

    # Download CSV
    csv_bytes = compiled_df.to_csv(index=False, encoding="utf-8-sig").encode()
    st.download_button("Download Compiled CSV", csv_bytes, "compiled.csv")

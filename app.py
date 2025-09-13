import streamlit as st
import pandas as pd
from io import BytesIO

st.title("CSV → Excel → Compiler")

# Step 1: Upload CSV files
csv_files = st.file_uploader(
    "Upload CSV files",
    type="csv",
    accept_multiple_files=True
)

excel_buffers = []

if csv_files:
    st.write("Converting CSV files to Excel...")
    for file in csv_files:
        # Read CSV safely
        try:
            df = pd.read_csv(file, dtype=str, on_bad_lines='skip', engine='python')
        except Exception as e:
            st.error(f"Failed to read {file.name}: {e}")
            continue

        # Clean all string columns
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].str.replace('=', '', regex=False).str.replace('"','', regex=False).str.strip()

        # Save to in-memory Excel
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        excel_buffers.append(buffer)

# Step 2: Compile all Excel files
if excel_buffers:
    dfs = []
    for buffer in excel_buffers:
        df = pd.read_excel(buffer, dtype=str)
        dfs.append(df)
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure important columns exist
    for col in ["EncounterID","FacilityCode","Balance","Age","CurrentPayer"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Convert numeric columns
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Level calculation
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

    # Sort by Balance
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    st.subheader("Compiled Data")
    st.dataframe(compiled_df)

    # Download
    csv_bytes = compiled_df.to_csv(index=False, encoding="utf-8-sig").encode()
    st.download_button("Download Compiled CSV", csv_bytes, "compiled.csv")

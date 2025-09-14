import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="CSV/Excel Compiler", layout="wide")
st.title("📊 CSV/Excel Day Start Compiler")

# --- Upload CSV or Excel ---
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# --- Helper to clean all string columns ---
def clean_df(df):
    df.columns = df.columns.str.strip().str.replace('"','').str.replace('=','')
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip().str.replace('"','').str.replace('=','')
    return df

# --- Robust CSV reader ---
def robust_read_csv(file):
    encodings = ['utf-8-sig','utf-8','utf-16','cp1252']
    for enc in encodings:
        try:
            df = pd.read_csv(file, encoding=enc, dtype=str, on_bad_lines='skip')
            return clean_df(df)
        except:
            continue
    raise ValueError(f"Cannot read CSV file: {file.name}")

# --- Excel reader ---
def read_excel_file(file):
    df = pd.read_excel(file, dtype=str)
    return clean_df(df)

# --- Process files ---
dfs = []
for file in uploaded_files:
    if file.name.endswith(".csv"):
        dfs.append(robust_read_csv(file))
    else:
        dfs.append(read_excel_file(file))

if dfs:
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure required columns
    for col in ["EncounterID","FacilityCode","CurrentPayer","Balance","Age"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Convert numeric columns safely
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Calculate Level
    def get_level(val):
        try:
            if pd.isna(val): return None
            val = float(val)
            if val <= 249.99: return "Level1"
            elif val <= 1999.99: return "Level2"
            elif val <= 9999.99: return "Level3"
            elif val <= 24999.99: return "Level4"
            else: return "Level5"
        except:
            return None
    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age>0
    compiled_df = compiled_df[compiled_df["Age"]>0]

    # Sort by Balance descending
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Display compiled data
    st.subheader("📝 Compiled Data")
    st.dataframe(compiled_df, width='stretch')

    # Pivot Table
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer","FacilityCode"]):
        for (payer, facility), group in compiled_df.groupby(["CurrentPayer","FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5","Level4","Level3","Level2","Level1"]:
                row[f"{lvl}_Count"] = group[group["Level"]==lvl].shape[0]
            row["Grand_Total_Count"] = group.shape[0]
            pivot_data.append(row)
    pivot_df = pd.DataFrame(pivot_data)

    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, width='stretch')

    # Download buttons
    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv")

import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Data Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# --- Utility Functions ---

def read_and_convert(file):
    """Read CSV/XLSX file. Convert CSV to Excel in memory."""
    if file.name.endswith(".csv"):
        # Read CSV
        df = pd.read_csv(file, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(file, dtype=str)
    return df

def clean_strings(df):
    """Remove = and " from all string/object columns and strip spaces."""
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False)\
                                      .str.replace('"', '', regex=False)\
                                      .str.strip()
    return df

def get_level(value):
    """Calculate level based on Balance value."""
    try:
        val = float(value)
        if val <= 249.99:
            return "Level1"
        elif val <= 1999.99:
            return "Level2"
        elif val <= 9999.99:
            return "Level3"
        elif val <= 24999.99:
            return "Level4"
        else:
            return "Level5"
    except:
        return None

# --- Main Processing ---

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = read_and_convert(file)
        df = clean_strings(df)
        dfs.append(df)

    # Compile all files
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Ensure important columns are string
    for col in ["EncounterID", "FacilityCode", "CurrentPayer"]:
        if col in compiled_df.columns:
            compiled_df[col] = compiled_df[col].astype(str).str.strip()

    # Convert Balance column (F) to numeric for Level calculation
    balance_col = compiled_df.columns[5]  # column F (0-indexed)
    compiled_df[balance_col] = compiled_df[balance_col].astype(str).str.replace(',', '', regex=False).str.strip()
    compiled_df[balance_col] = pd.to_numeric(compiled_df[balance_col], errors='coerce')

    # Apply Level calculation in column T
    compiled_df["Level"] = compiled_df[balance_col].apply(get_level)

    # Convert Age column to numeric
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Filter Age > 0
    df_filtered = compiled_df[compiled_df["Age"] > 0] if "Age" in compiled_df.columns else compiled_df

    # Sort by Balance descending and reset index
    compiled_df.sort_values(by=balance_col, ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Display compiled data (Arrow-compatible)
    compiled_df_display = compiled_df.astype(str)
    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df_display, width='stretch')

    # --- Pivot Table ---
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode", "EncounterID", "Level"]):
        for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)
    pivot_df = pd.DataFrame(pivot_data).astype(str)
    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, width='stretch')

    # --- Download Functions ---
    def convert_df_to_csv(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button(
        "⬇️ Download Compiled Data (CSV)",
        convert_df_to_csv(compiled_df),
        "compiled_data.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download Pivot Table (CSV)",
        convert_df_to_csv(pivot_df),
        "pivot_table.csv",
        "text/csv"
    )

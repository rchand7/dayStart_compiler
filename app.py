import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# Read CSV or Excel
def read_file(file):
    if file.name.endswith(".csv"):
        # Read CSV safely, skip bad lines
        return pd.read_csv(file, on_bad_lines='skip')
    else:
        return pd.read_excel(file)

# Clean string columns
def clean_strings(df):
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = (
            df[col].astype(str)
                  .str.replace('=', '', regex=False)
                  .str.replace('"', '', regex=False)
                  .str.strip()
        )
    return df

# Level calculation function
def get_level(value):
    try:
        if pd.isna(value):
            return None
        if value <= 249.99:
            return "Level1"
        elif value <= 1999.99:
            return "Level2"
        elif value <= 9999.99:
            return "Level3"
        elif value <= 24999.99:
            return "Level4"
        else:
            return "Level5"
    except:
        return None

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = read_file(file)
        df = clean_strings(df)
        dfs.append(df)

    # Compile all files
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Ensure key columns as string
    for col in ["FacilityCode", "CurrentPayer", "EncounterID"]:
        if col in compiled_df.columns:
            compiled_df[col] = compiled_df[col].astype(str).str.strip()

    # Convert Balance column (F) to numeric
    balance_col = "Balance"
    if balance_col in compiled_df.columns:
        compiled_df[balance_col] = (
            compiled_df[balance_col]
            .astype(str)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        compiled_df[balance_col] = pd.to_numeric(compiled_df[balance_col], errors='coerce')

    # Apply Level calculation (T column)
    compiled_df["Level"] = compiled_df[balance_col].apply(get_level)

    # Ensure numeric Age for filtering
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")
    df_filtered = compiled_df[compiled_df["Age"] > 0]

    # Sort by Balance descending
    compiled_df.sort_values(by=balance_col, ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Set EncounterID as index
    if "EncounterID" in compiled_df.columns:
        compiled_df.set_index("EncounterID", inplace=True)

    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df, width="stretch")

    # Pivot table
    pivot_data = []
    if all(col in df_filtered.columns for col in ["CurrentPayer", "FacilityCode", "EncounterID"]):
        for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)

    st.subheader("📌 Effective Pivot Table (Count)")
    st.dataframe(pivot_df, width="stretch")

    # Download functions
    def convert_df(df):
        return df.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button(
        "⬇️ Download Compiled Data (Sorted by Balance)",
        convert_df(compiled_df),
        "compiled_data_sorted.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download Pivot Table",
        convert_df(pivot_df),
        "pivot_table.csv",
        "text/csv"
    )

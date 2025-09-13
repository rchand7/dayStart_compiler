import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Day Start and Day End Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# --- File uploader ---
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# --- Read files ---
def read_file(file):
    if file.name.endswith(".csv"):
        # Read CSV with proper parsing
        df = pd.read_csv(file, quotechar='"', on_bad_lines='skip')
    else:
        df = pd.read_excel(file)
    return df

# --- Clean string columns ---
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

# --- Level calculation ---
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

    # --- Combine all files ---
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # --- Convert Balance column to numeric ---
    if "Balance" in compiled_df.columns:
        compiled_df["Balance"] = (
            compiled_df["Balance"]
            .astype(str)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"], errors='coerce')

    # --- Apply Level ---
    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # --- Ensure numeric Age for filtering ---
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")
        df_filtered = compiled_df[compiled_df["Age"] > 0].copy()
    else:
        df_filtered = compiled_df.copy()

    # --- Sort by Balance descending ---
    compiled_df.sort_values(by="Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # --- Use EncounterID as index if exists ---
    if "EncounterID" in compiled_df.columns:
        compiled_df.set_index("EncounterID", inplace=True)

    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df)

    # --- Pivot table ---
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode"]):
        for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group.shape[0]
            row["Grand_Total_Count"] = group.shape[0]
            pivot_data.append(row)
    pivot_df = pd.DataFrame(pivot_data)

    st.subheader("📌 Effective Pivot Table (Count)")
    st.dataframe(pivot_df)

    # --- Download ---
    def convert_df(df):
        return df.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button(
        "⬇️ Download Compiled Data",
        convert_df(compiled_df),
        "compiled_data.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download Pivot Table",
        convert_df(pivot_df),
        "pivot_table.csv",
        "text/csv"
    )

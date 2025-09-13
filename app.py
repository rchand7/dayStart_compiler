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
        return pd.read_csv(file)
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

# Level calculation
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
    # Read and clean all files
    dfs = []
    for file in uploaded_files:
        df = read_file(file)
        df = clean_strings(df)
        dfs.append(df)

    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Ensure ID and key columns remain string
    for col in ["FacilityCode", "CurrentPayer"]:
        if col in compiled_df.columns:
            compiled_df[col] = compiled_df[col].astype(str).str.strip()

    # Convert numeric column (6th column) for Level calculation
    col_index = 5
    compiled_df.iloc[:, col_index] = (
        compiled_df.iloc[:, col_index]
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.strip()
    )
    compiled_df.iloc[:, col_index] = pd.to_numeric(compiled_df.iloc[:, col_index], errors='coerce')

    # Apply Level function
    compiled_df["Level"] = compiled_df.iloc[:, col_index].apply(get_level)

    # Ensure Balance and Age numeric
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"], errors="coerce")
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")

    # Filter Age > 0
    df_filtered = compiled_df[compiled_df["Age"] > 0]

    # Sort compiled data by Balance descending
    compiled_df.sort_values(by="Balance", ascending=False, inplace=True)

    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df, use_container_width=True)

    # Pivot table
    pivot_data = []
    if "CurrentPayer" in compiled_df.columns and "FacilityCode" in compiled_df.columns:
        for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)

    st.subheader("📌 Effective Pivot Table (Count)")
    st.dataframe(pivot_df, use_container_width=True)

    # Download function
    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

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

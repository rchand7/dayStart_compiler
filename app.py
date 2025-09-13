import streamlit as st
import pandas as pd

st.set_page_config(page_title=" Data Compiler", layout="wide")

st.title("📊 Day Start and Day End Compiler ")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# Utility function
def read_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

if uploaded_files:
    dfs = [read_file(file) for file in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True)

    # Remove only fully identical rows
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Level formula on column F (6th column, index 5)
    def get_level(value):
        try:
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

    compiled_df["Level"] = compiled_df.iloc[:, 5].apply(get_level)

    st.subheader("📝 Compiled Data with Levels")
    st.dataframe(compiled_df, use_container_width=True)

    # Ensure numeric
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"], errors="coerce")
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")

    # Filter Age > 0
    df_filtered = compiled_df[compiled_df["Age"] > 0]

    # Create effective pivot
    pivot_data = []

    for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
        row = {"CurrentPayer": payer, "FacilityCode": facility}
        for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
            lvl_group = group[group["Level"] == lvl]
            row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
        row["Grand_Total_Count"] = group["EncounterID"].count()
        pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)

    # Format balances
    balance_cols = [col for col in pivot_df.columns if "Balance" in col]
    for col in balance_cols:
        pivot_df[col] = pivot_df[col].apply(lambda x: f"${x:,.2f}")

    st.subheader("📌 Effective Pivot Table (Count )")
    st.dataframe(pivot_df, use_container_width=True)

    # --- Download Options ---
    def convert_df(df):
        return df.to_csv(index=False).encode("utf-8")

    # Download compiled data
    st.download_button(
        "⬇️ Download Compiled Data",
        convert_df(compiled_df),
        "compiled_data.csv",
        "text/csv"
    )

    # Download pivot table
    st.download_button(
        "⬇️ Download Pivot Table",
        convert_df(pivot_df),
        "pivot_table.csv",
        "text/csv"
    )


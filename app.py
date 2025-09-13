import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Data Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

uploaded_files = st.file_uploader(
    "Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True
)

def read_csv_as_excel(file):
    """Read CSV as string, clean it, then save to in-memory Excel"""
    df = pd.read_csv(file, dtype=str, keep_default_na=False)
    # Remove = and " from all string columns
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    # Save to Excel in memory
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return pd.read_excel(excel_buffer, dtype=str)

def get_level(balance):
    try:
        b = float(balance)
        if b <= 249.99:
            return "Level1"
        elif b <= 1999.99:
            return "Level2"
        elif b <= 9999.99:
            return "Level3"
        elif b <= 24999.99:
            return "Level4"
        else:
            return "Level5"
    except:
        return None

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        if file.name.endswith(".csv"):
            df = read_csv_as_excel(file)
        else:
            df = pd.read_excel(file, dtype=str)
            # Clean strings for Excel too
            str_cols = df.select_dtypes(include='object').columns
            for col in str_cols:
                df[col] = df[col].str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
        dfs.append(df)

    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Convert Balance column (F) to numeric
    balance_col = compiled_df.columns[5]
    compiled_df[balance_col] = pd.to_numeric(compiled_df[balance_col].str.replace(',', '', regex=False), errors='coerce')

    # Level column (T)
    compiled_df["Level"] = compiled_df[balance_col].apply(get_level)

    # Sort by Balance
    compiled_df.sort_values(by=balance_col, ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    st.subheader("Compiled Data")
    st.dataframe(compiled_df.astype(str), width='stretch')

    # Pivot Table
    if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode", "EncounterID", "Level"]):
        pivot_data = []
        for (payer, facility), group in compiled_df.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                row[f"{lvl}_Count"] = group[group["Level"] == lvl]["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)
        pivot_df = pd.DataFrame(pivot_data)
        st.subheader("Pivot Table")
        st.dataframe(pivot_df.astype(str), width='stretch')

    # Downloads
    def convert_csv(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("Download Compiled Data", convert_csv(compiled_df), "compiled.csv", "text/csv")
    if 'pivot_df' in locals():
        st.download_button("Download Pivot Table", convert_csv(pivot_df), "pivot.csv", "text/csv")

import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Data Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more CSV or Excel files",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# Convert CSV to in-memory Excel and clean strings
def csv_to_excel_in_memory(file):
    # Read CSV with python engine to handle irregular CSVs
    df = pd.read_csv(file, engine='python', dtype=str, on_bad_lines='skip')
    # Clean all string columns
    df = df.applymap(lambda x: str(x).replace('=', '').replace('"', '').strip())
    # Save to Excel in memory
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output

# Read file (CSV or Excel) and clean strings
def read_file(file):
    if file.name.endswith(".csv"):
        excel_file = csv_to_excel_in_memory(file)
        df = pd.read_excel(excel_file, dtype=str)
    else:
        df = pd.read_excel(file, dtype=str)
    # Clean all string columns again
    df = df.applymap(lambda x: str(x).replace('=', '').replace('"', '').strip())
    return df

# Level calculation
def get_level(value):
    try:
        value = float(value)
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
        dfs.append(df)

    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Ensure key columns
    for col in ["FacilityCode", "CurrentPayer", "EncounterID"]:
        if col in compiled_df.columns:
            compiled_df[col] = compiled_df[col].astype(str).str.strip()

    # Convert Balance column to numeric
    if "Balance" in compiled_df.columns:
        compiled_df["Balance"] = compiled_df["Balance"].str.replace(',', '').astype(float)

    # Apply Level calculation
    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age > 0 if Age exists
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")
        compiled_df = compiled_df[compiled_df["Age"] > 0]

    # Sort by Balance descending
    if "Balance" in compiled_df.columns:
        compiled_df.sort_values(by="Balance", ascending=False, inplace=True)

    # Reset index and make EncounterID the first column
    if "EncounterID" in compiled_df.columns:
        compiled_df.insert(0, "EncounterID", compiled_df.pop("EncounterID"))
    compiled_df.reset_index(drop=True, inplace=True)

    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df, width=None)

    # Pivot Table
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode", "Level", "EncounterID"]):
        for (payer, facility), group in compiled_df.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)
    st.subheader("📌 Effective Pivot Table (Count)")
    st.dataframe(pivot_df, width=None)

    # Download CSV
    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

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

import streamlit as st
import pandas as pd
import csv
from io import StringIO

st.set_page_config(page_title="Day Start Compiler", layout="wide")
st.title("📊 Day Start and Da- End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# Function to detect CSV delimiter
def detect_delimiter(file):
    first_bytes = file.read(1024)
    file.seek(0)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(first_bytes.decode('utf-8'))
        return dialect.delimiter
    except:
        return ','

# Function to read a file robustly
def read_file(file):
    if file.name.endswith(".csv"):
        delimiter = detect_delimiter(file)
        df = pd.read_csv(
            file,
            delimiter=delimiter,
            dtype=str,  # Force all columns as string
            converters={"EncounterID": str}
        )
    else:
        df = pd.read_excel(file, dtype=str)
    
    # Clean strings
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    
    if "EncounterID" in df.columns:
        df["EncounterID"] = df["EncounterID"].astype(str).str.strip()
    
    return df

# Level calculation
def get_level(value):
    try:
        if pd.isna(value):
            return None
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

    # Convert Balance to numeric
    if "Balance" in compiled_df.columns:
        compiled_df["Balance"] = compiled_df["Balance"].str.replace(',', '', regex=False).astype(float)
        compiled_df["Level"] = compiled_df["Balance"].apply(get_level)
    
    # Age numeric
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')
        df_filtered = compiled_df[compiled_df["Age"] > 0]
    else:
        df_filtered = compiled_df.copy()
    
    # Sort by Balance
    if "Balance" in compiled_df.columns:
        compiled_df.sort_values(by="Balance", ascending=False, inplace=True)
    
    st.subheader("📝 Compiled Data with Levels")
    st.dataframe(compiled_df, use_container_width=True)

    # Pivot table
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode"]):
        for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group["Level"] == lvl]
                row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
            row["Grand_Total_Count"] = group["EncounterID"].count()
            pivot_data.append(row)
    
    pivot_df = pd.DataFrame(pivot_data)
    
    st.subheader("📌 Pivot Table (Count)")
    st.dataframe(pivot_df, use_container_width=True)

    # Download CSVs
    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    
    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv", "text/csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv", "text/csv")

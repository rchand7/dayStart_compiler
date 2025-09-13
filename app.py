import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Day Start Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# Read CSV or Excel robustly
def read_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(
            file,
            dtype=str,               # Force everything as string
            on_bad_lines='skip',     # Skip malformed lines
            quoting=0                # Minimal quoting
        )
    else:
        df = pd.read_excel(file, dtype=str)
    
    # Clean string columns
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    
    if "EncounterID" in df.columns:
        df["EncounterID"] = df["EncounterID"].astype(str).str.strip()
    
    return df

# Level calculation function
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
    dfs = [read_file(f) for f in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)

    # Ensure numeric Balance and calculate Level
    if "Balance" in compiled_df.columns:
        compiled_df["Balance"] = compiled_df["Balance"].str.replace(',', '', regex=False).astype(float)
        compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Ensure numeric Age
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')
        df_filtered = compiled_df[compiled_df["Age"] > 0]
    else:
        df_filtered = compiled_df.copy()

    # Sort by Balance descending
    if "Balance" in compiled_df.columns:
        compiled_df.sort_values(by="Balance", ascending=False, inplace=True)

    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
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

    # Download as Excel with proper formatting
    def to_excel(df_main, df_pivot):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, index=False, sheet_name='Compiled Data')
            df_pivot.to_excel(writer, index=False, sheet_name='Pivot Table')
            writer.save()
        processed_data = output.getvalue()
        return processed_data

    excel_data = to_excel(compiled_df, pivot_df)

    st.download_button(
        label="⬇️ Download Compiled Data & Pivot Table (Excel)",
        data=excel_data,
        file_name="Compiled_Data_with_Pivot.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

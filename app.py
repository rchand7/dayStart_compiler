import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Data Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# File uploader
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True
)

# Function to read CSV or Excel and convert CSV to DataFrame correctly
def read_file(file):
    if file.name.endswith(".csv"):
        try:
            # Auto-detect separator, engine='python' handles irregular CSVs
            df = pd.read_csv(file, sep=None, engine='python', dtype=str, on_bad_lines='skip')
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            return pd.DataFrame()
    else:
        df = pd.read_excel(file, dtype=str)
    return df

# Clean string columns
def clean_strings(df):
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
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
        if df.empty:
            continue
        df = clean_strings(df)
        dfs.append(df)

    if not dfs:
        st.warning("No valid data to compile.")
    else:
        compiled_df = pd.concat(dfs, ignore_index=True)
        compiled_df.drop_duplicates(keep='first', inplace=True)

        # Ensure key columns exist
        for col in ["EncounterID", "FacilityCode", "CurrentPayer", "Balance", "Age"]:
            if col not in compiled_df.columns:
                compiled_df[col] = None

        # Convert Balance to numeric
        compiled_df['Balance'] = compiled_df['Balance'].str.replace(',', '', regex=False)
        compiled_df['Balance'] = pd.to_numeric(compiled_df['Balance'], errors='coerce')

        # Apply Level
        compiled_df['Level'] = compiled_df['Balance'].apply(get_level)

        # Convert Age to numeric
        compiled_df['Age'] = pd.to_numeric(compiled_df['Age'], errors='coerce')

        # Filter Age > 0
        df_filtered = compiled_df[compiled_df['Age'] > 0]

        # Sort by Balance descending and reset index
        compiled_df.sort_values(by='Balance', ascending=False, inplace=True)
        compiled_df.reset_index(drop=True, inplace=True)

        st.subheader("📝 Compiled Data")
        st.dataframe(compiled_df, width=1000)

        # Pivot table
        pivot_data = []
        if all(col in compiled_df.columns for col in ["CurrentPayer", "FacilityCode", "EncounterID"]):
            for (payer, facility), group in df_filtered.groupby(["CurrentPayer", "FacilityCode"]):
                row = {"CurrentPayer": payer, "FacilityCode": facility}
                for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                    lvl_group = group[group["Level"] == lvl]
                    row[f"{lvl}_Count"] = lvl_group["EncounterID"].count()
                row["Grand_Total_Count"] = group["EncounterID"].count()
                pivot_data.append(row)

        pivot_df = pd.DataFrame(pivot_data)
        st.subheader("📌 Pivot Table")
        st.dataframe(pivot_df, width=1000)

        # Download function
        def convert_df(df):
            return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

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

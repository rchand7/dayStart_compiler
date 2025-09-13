import streamlit as st
import pandas as pd

st.set_page_config(page_title="Day Start Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

# --- File uploader ---
uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

# --- Function to read files ---
def read_file(file):
    if file.name.endswith(".csv"):
        # Read CSV with converters to force EncounterID as string
        try:
            df = pd.read_csv(
                file,
                sep=None,  # Auto-detect separator
                engine='python',
                converters={"EncounterID": str},
                dtype=str  # Force all columns as string
            )
        except:
            df = pd.read_csv(file, dtype=str)
    else:
        # Excel
        df = pd.read_excel(file, dtype=str)
    
    # Clean all string columns
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    
    # Ensure EncounterID is string
    if "EncounterID" in df.columns:
        df["EncounterID"] = df["EncounterID"].astype(str).str.strip()
    
    return df

# --- Clean other string columns ---
def clean_strings(df):
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
    return df

# --- Level calculation ---
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
        
        # Standardize column names
        df.columns = df.columns.str.strip().str.replace(' ', '').str.replace('_', '')
        
        # Clean other string columns
        df = clean_strings(df)
        
        # Convert Balance to numeric
        if "Balance" in df.columns:
            df["Balance"] = df["Balance"].str.replace(',', '', regex=False).str.strip()
            df["Balance"] = pd.to_numeric(df["Balance"], errors='coerce')
        
        dfs.append(df)
    
    # Concatenate all files
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep="first", inplace=True)
    
    # Apply Level calculation
    if "Balance" in compiled_df.columns:
        compiled_df["Level"] = compiled_df["Balance"].apply(get_level)
    
    # Ensure Age numeric
    if "Age" in compiled_df.columns:
        compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors="coerce")
        df_filtered = compiled_df[compiled_df["Age"] > 0]
    else:
        df_filtered = compiled_df.copy()
    
    # Sort by Balance descending
    if "Balance" in compiled_df.columns:
        compiled_df.sort_values(by="Balance", ascending=False, inplace=True)
    
    # Show compiled data
    st.subheader("📝 Compiled Data with Levels (Sorted by Balance)")
    st.dataframe(compiled_df, use_container_width=True)
    
    # --- Pivot Table ---
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
    
    st.subheader("📌 Effective Pivot Table (Count)")
    st.dataframe(pivot_df, use_container_width=True)
    
    # --- Download function ---
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

import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="CSV to Excel Compiler", layout="wide")
st.title("📊 CSV to Excel Converter & Day Start Compiler")

# --- Step 1: CSV to Excel ---
st.subheader("Step 1: Convert CSV files to Excel")

csv_files = st.file_uploader(
    "Upload CSV files to convert", type=["csv"], accept_multiple_files=True, key="csv_convert"
)

converted_excel_files = []

if csv_files:
    st.write("✅ Converting CSV to Excel...")
    for file in csv_files:
        try:
            df = pd.read_csv(file, dtype=str, quotechar='"', on_bad_lines='skip', keep_default_na=False)
            # Clean all string columns
            df = df.applymap(lambda x: x.replace('=', '').replace('"','').strip() if isinstance(x,str) else x)
            # Convert to in-memory Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            converted_excel_files.append(output)
            st.success(f"{file.name} converted successfully")
        except Exception as e:
            st.error(f"Failed to convert {file.name}: {e}")

# --- Step 2: Upload Excel files for compilation ---
st.subheader("Step 2: Upload Excel files (original or converted)")

excel_files = st.file_uploader(
    "Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel_compile"
)

# Include converted CSVs
if converted_excel_files:
    excel_files = excel_files + converted_excel_files if excel_files else converted_excel_files

# --- Step 3: Compilation ---
if excel_files:
    dfs = []
    for file in excel_files:
        try:
            df = pd.read_excel(file, dtype=str)
            df = df.applymap(lambda x: x.replace('=', '').replace('"','').strip() if isinstance(x,str) else x)
            dfs.append(df)
        except Exception as e:
            st.error(f"Failed to read file: {e}")

    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure required columns
    for col in ["EncounterID","FacilityCode","CurrentPayer","Balance","Age"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Numeric conversions
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].astype(str).str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Level calculation
    def get_level(val):
        try:
            if pd.isna(val): return None
            val = float(val)
            if val <= 249.99: return "Level1"
            elif val <= 1999.99: return "Level2"
            elif val <= 9999.99: return "Level3"
            elif val <= 24999.99: return "Level4"
            else: return "Level5"
        except: return None

    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age>0
    compiled_df = compiled_df[compiled_df["Age"]>0]

    # Sort by Balance descending
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Display compiled data
    st.subheader("📝 Compiled Data")
    st.dataframe(compiled_df, width='stretch')

    # Pivot table
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer","FacilityCode"]):
        for (payer, facility), group in compiled_df.groupby(["CurrentPayer","FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5","Level4","Level3","Level2","Level1"]:
                row[f"{lvl}_Count"] = group[group["Level"]==lvl].shape[0]
            row["Grand_Total_Count"] = group.shape[0]
            pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)
    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, width='stretch')

    # Download buttons
    def to_csv(df):
        return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

    st.download_button("⬇️ Download Compiled Data", to_csv(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", to_csv(pivot_df), "pivot_table.csv")

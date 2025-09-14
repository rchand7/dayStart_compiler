import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="CSV to Excel Compiler", layout="wide")
st.title("📊 CSV to Excel Converter & Day Start Compiler")

# --- Step 1: CSV to Excel Converter ---
st.subheader("Step 1: Convert CSV files to Excel")

csv_files = st.file_uploader(
    "Upload CSV files to convert to Excel", 
    type=["csv"], 
    accept_multiple_files=True,
    key="csv_convert"
)

converted_excel_files = []

if csv_files:
    st.write("✅ Converting CSV to Excel...")
    for file in csv_files:
        try:
            df = pd.read_csv(file, quotechar='"', on_bad_lines='skip')
            # Clean string columns
            for col in df.select_dtypes(include='object').columns:
                df[col] = df[col].astype(str).str.replace('=','').str.replace('"','').str.strip()
            # Convert to in-memory Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            converted_excel_files.append((file.name.replace(".csv", ".xlsx"), output))
            st.success(f"Converted {file.name} to Excel")
        except Exception as e:
            st.error(f"Failed to convert {file.name}: {e}")

# --- Step 2: Upload Excel files for compilation ---
st.subheader("Step 2: Upload Excel files (original or converted)")

excel_files = st.file_uploader(
    "Upload Excel files for compilation",
    type=["xlsx"],
    accept_multiple_files=True,
    key="excel_compile"
)

# Include converted files in the list
if converted_excel_files:
    for name, excel_io in converted_excel_files:
        excel_files.append(excel_io)

# --- Step 3: Compile Data ---
if excel_files:
    dfs = []
    for file in excel_files:
        df = pd.read_excel(file)
        # Clean string columns
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.replace('=','').str.replace('"','').str.strip()
        dfs.append(df)

    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure required columns exist
    for col in ["EncounterID","FacilityCode","CurrentPayer","Balance","Age"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Numeric conversion
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].astype(str).str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Level calculation
    def get_level(value):
        try:
            if pd.isna(value): return None
            value = float(value)
            if value <= 249.99: return "Level1"
            elif value <= 1999.99: return "Level2"
            elif value <= 9999.99: return "Level3"
            elif value <= 24999.99: return "Level4"
            else: return "Level5"
        except:
            return None

    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age>0
    compiled_df = compiled_df[compiled_df["Age"]>0]

    # Sort by Balance descending
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # --- Display compiled data ---
    st.subheader("📝 Compiled Data")
    st.dataframe(compiled_df, width="stretch")

    # --- Pivot Table ---
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
    st.dataframe(pivot_df, width="stretch")

    # --- Download Buttons ---
    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv")

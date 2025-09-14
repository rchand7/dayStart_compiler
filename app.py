import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Day Start Compiler", layout="wide")
st.title("📊 CSV/Excel Compiler with EncounterID Fix")

# Step 1: Upload CSV or Excel
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

def clean_df(df):
    # Standardize column names
    df.columns = df.columns.str.strip().str.replace(' ', '').str.replace('"','').str.replace('=','')
    
    # Ensure key columns exist
    for col in ["EncounterID", "FacilityCode", "Balance", "Age", "CurrentPayer"]:
        if col not in df.columns:
            df[col] = None

    # Clean string columns
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().str.replace('=', '').str.replace('"','')

    # Ensure Balance and Age numeric
    df["Balance"] = pd.to_numeric(df["Balance"].astype(str).str.replace(',', ''), errors='coerce')
    df["Age"] = pd.to_numeric(df["Age"], errors='coerce')

    return df

# Convert CSV to Excel in-memory
def csv_to_excel(file):
    df = pd.read_csv(file, quotechar='"', on_bad_lines='skip', encoding='utf-8')
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

# Read all files
dfs = []
for file in uploaded_files:
    try:
        if file.name.endswith(".csv"):
            excel_io = csv_to_excel(file)
            df = pd.read_excel(excel_io)
        else:
            df = pd.read_excel(file)
        df = clean_df(df)
        dfs.append(df)
    except Exception as e:
        st.error(f"Failed to process {file.name}: {e}")

if dfs:
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Filter Age > 0
    compiled_df = compiled_df[compiled_df["Age"]>0]

    # Level calculation
    def get_level(balance):
        if pd.isna(balance): return None
        if balance <= 249.99: return "Level1"
        elif balance <= 1999.99: return "Level2"
        elif balance <= 9999.99: return "Level3"
        elif balance <= 24999.99: return "Level4"
        else: return "Level5"

    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Sort by Balance descending
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Set EncounterID as index (optional)
    if "EncounterID" in compiled_df.columns:
        compiled_df.set_index("EncounterID", inplace=True)

    # Display
    st.subheader("📝 Compiled Data")
    st.dataframe(compiled_df)  # no width param, avoids StreamlitInvalidWidthError

    # Pivot Table
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
    st.dataframe(pivot_df)

    # Download buttons
    def convert_df(df):
        return df.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv")

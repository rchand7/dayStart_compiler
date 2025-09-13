import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Day Start and Day End Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

def read_file_as_excel(file):
    # Read CSV as DataFrame and convert to Excel in memory
    if file.name.endswith(".csv"):
        df = pd.read_csv(file, quotechar='"', on_bad_lines='skip')
    else:
        df = pd.read_excel(file)
    # Clean headers
    df.columns = [str(c).strip().replace('"','').replace('=','') for c in df.columns]
    # Clean string data
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.replace('"','').str.replace('=','').str.strip()
    # Convert DataFrame to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    # Read it back as Excel to standardize
    return pd.read_excel(output)

def get_level(value):
    try:
        if pd.isna(value):
            return None
        value = float(value)
        if value <= 249.99: return "Level1"
        elif value <= 1999.99: return "Level2"
        elif value <= 9999.99: return "Level3"
        elif value <= 24999.99: return "Level4"
        else: return "Level5"
    except:
        return None

if uploaded_files:
    dfs = [read_file_as_excel(file) for file in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    
    # Ensure columns exist
    for col in ["EncounterID","FacilityCode","CurrentPayer","Balance","Age"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].astype(str).str.replace(',',''), errors='coerce')
    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')
    
    # Filter Age>0
    df_filtered = compiled_df[compiled_df["Age"]>0].copy()
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)
    
    st.subheader("📝 Compiled Data with Levels")
    st.dataframe(compiled_df)

    # Pivot
    pivot_data = []
    if all(col in df_filtered.columns for col in ["CurrentPayer","FacilityCode"]):
        for (payer,facility), group in df_filtered.groupby(["CurrentPayer","FacilityCode"]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5","Level4","Level3","Level2","Level1"]:
                row[f"{lvl}_Count"] = group[group["Level"]==lvl].shape[0]
            row["Grand_Total_Count"] = group.shape[0]
            pivot_data.append(row)
    pivot_df = pd.DataFrame(pivot_data)
    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df)

    def convert_df(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv")

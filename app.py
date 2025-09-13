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

def clean_dataframe(df):
    # Clean headers
    df.columns = [str(c).strip().replace('=','').replace('"','') for c in df.columns]
    # Clean all string data
    str_cols = df.select_dtypes(include='object').columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.replace('=','').str.replace('"','').str.strip()
    return df

def read_as_excel(file):
    if file.name.endswith(".csv"):
        # Read CSV safely with quotes and skip bad lines
        df = pd.read_csv(file, quotechar='"', on_bad_lines='skip')
    else:
        df = pd.read_excel(file)
    df = clean_dataframe(df)

    # Convert to in-memory Excel to standardize
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
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
    dfs = [read_as_excel(f) for f in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # Ensure important columns exist
    for col in ["EncounterID","FacilityCode","CurrentPayer","Balance","Age"]:
        if col not in compiled_df.columns:
            compiled_df[col] = None

    # Convert Balance and Age to numeric
    compiled_df["Balance"] = pd.to_numeric(compiled_df["Balance"].astype(str).str.replace(',',''), errors='coerce')
    compiled_df["Age"] = pd.to_numeric(compiled_df["Age"], errors='coerce')

    # Apply Level
    compiled_df["Level"] = compiled_df["Balance"].apply(get_level)

    # Filter Age>0
    compiled_df = compiled_df[compiled_df["Age"]>0]

    # Sort by Balance descending and reset index
    compiled_df.sort_values("Balance", ascending=False, inplace=True)
    compiled_df.reset_index(drop=True, inplace=True)

    # Display compiled data
    st.subheader("📝 Compiled Data with Levels")
    st.dataframe(compiled_df)

    # Create pivot
    pivot_data = []
    if all(col in compiled_df.columns for col in ["CurrentPayer","FacilityCode"]):
        for (payer,facility), group in compiled_df.groupby(["CurrentPayer","FacilityCode"]):
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
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    st.download_button("⬇️ Download Compiled Data", convert_df(compiled_df), "compiled_data.csv")
    st.download_button("⬇️ Download Pivot Table", convert_df(pivot_df), "pivot_table.csv")

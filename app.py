import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Day Start Compiler", layout="wide")
st.title("📊 Day Start and Day End Compiler")

uploaded_files = st.file_uploader(
    "Upload one or more files (CSV/Excel)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

def read_file(file):
    # Read CSV or Excel
    if file.name.endswith(".csv"):
        # Read CSV as strings and immediately convert to Excel-like DataFrame
        df = pd.read_csv(file, dtype=str, engine='python', on_bad_lines='skip')
    else:
        df = pd.read_excel(file, dtype=str)
    
    # Clean string columns
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    
    return df

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
    
    # Compile all files
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep='first', inplace=True)

    # Map columns by position: A=EncounterID, B=FacilityCode, F=Balance
    col_map = {}
    if compiled_df.shape[1] >= 6:
        col_map['EncounterID'] = compiled_df.columns[0]
        col_map['FacilityCode'] = compiled_df.columns[1]
        col_map['Balance'] = compiled_df.columns[5]

    # Ensure columns are clean
    for key in col_map:
        compiled_df[col_map[key]] = compiled_df[col_map[key]].astype(str).str.strip().str.replace('=', '', regex=False).str.replace('"', '', regex=False)

    # Convert Balance to numeric
    compiled_df['Balance_numeric'] = pd.to_numeric(compiled_df[col_map['Balance']], errors='coerce')
    
    # Calculate Level
    compiled_df['Level'] = compiled_df['Balance_numeric'].apply(get_level)

    # Sort by Balance descending
    compiled_df.sort_values(by='Balance_numeric', ascending=False, inplace=True)

    st.subheader("📝 Compiled Data (Sorted by Balance)")
    st.dataframe(compiled_df, width="stretch")

    # Pivot table
    pivot_data = []
    for (payer, facility), group in compiled_df.groupby([compiled_df.columns[2] if 'CurrentPayer' not in compiled_df.columns else 'CurrentPayer', col_map['FacilityCode']]):
        row = {"CurrentPayer": payer, "FacilityCode": facility}
        for lvl in ["Level5","Level4","Level3","Level2","Level1"]:
            lvl_group = group[group['Level']==lvl]
            row[f"{lvl}_Count"] = lvl_group[col_map['EncounterID']].count()
        row["Grand_Total_Count"] = group[col_map['EncounterID']].count()
        pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)
    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, width="stretch")

    # Download Excel
    def to_excel(df_main, df_pivot):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, index=False, sheet_name='Compiled Data')
            df_pivot.to_excel(writer, index=False, sheet_name='Pivot Table')
        return output.getvalue()

    excel_data = to_excel(compiled_df, pivot_df)

    st.download_button(
        "⬇️ Download Compiled Data & Pivot Table (Excel)",
        data=excel_data,
        file_name="Compiled_Data_with_Pivot.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

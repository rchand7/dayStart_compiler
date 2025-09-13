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
    if file.name.endswith(".csv"):
        df = pd.read_csv(
            file,
            sep=None,              # Auto-detect separator
            engine='python',       # Python engine handles irregular CSVs
            dtype=str,             # Keep all as string
            on_bad_lines='skip',   # Skip malformed lines
        )
    else:
        df = pd.read_excel(file, dtype=str)
    
    # Clean all string columns
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
    # Read and compile all files
    dfs = [read_file(f) for f in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True)
    compiled_df.drop_duplicates(keep='first', inplace=True)

    # Map columns by position if headers are different
    # A = EncounterID, B = FacilityCode, F = Balance, T = Level (to be calculated)
    col_map = {}
    if compiled_df.shape[1] >= 6:
        col_map['EncounterID'] = compiled_df.columns[0]  # Column A
        col_map['FacilityCode'] = compiled_df.columns[1]  # Column B
        col_map['Balance'] = compiled_df.columns[5]  # Column F

    # Clean mapped columns
    for key in col_map:
        compiled_df[col_map[key]] = compiled_df[col_map[key]].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()

    # Convert Balance to numeric for Level
    compiled_df['Balance_numeric'] = pd.to_numeric(compiled_df[col_map['Balance']], errors='coerce')
    compiled_df['Level'] = compiled_df['Balance_numeric'].apply(get_level)

    # Filter Age if exists
    if 'Age' in compiled_df.columns:
        compiled_df['Age'] = pd.to_numeric(compiled_df['Age'], errors='coerce')
        df_filtered = compiled_df[compiled_df['Age'] > 0]
    else:
        df_filtered = compiled_df.copy()

    # Sort by Balance descending
    compiled_df.sort_values(by='Balance_numeric', ascending=False, inplace=True)

    # Display compiled data
    st.subheader("📝 Compiled Data (Sorted by Balance)")
    st.dataframe(compiled_df, width="stretch")

    # Pivot table
    pivot_data = []
    if 'FacilityCode' in col_map and 'EncounterID' in col_map:
        for (payer, facility), group in df_filtered.groupby([compiled_df.columns[2] if 'CurrentPayer' not in compiled_df.columns else 'CurrentPayer', col_map['FacilityCode']]):
            row = {"CurrentPayer": payer, "FacilityCode": facility}
            for lvl in ["Level5", "Level4", "Level3", "Level2", "Level1"]:
                lvl_group = group[group['Level'] == lvl]
                row[f"{lvl}_Count"] = lvl_group[col_map['EncounterID']].count()
            row["Grand_Total_Count"] = group[col_map['EncounterID']].count()
            pivot_data.append(row)

    pivot_df = pd.DataFrame(pivot_data)
    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, width="stretch")

    # Excel download
    def to_excel(df_main, df_pivot):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, index=False, sheet_name='Compiled Data')
            pivot_df.to_excel(writer, index=False, sheet_name='Pivot Table')
        return output.getvalue()

    excel_data = to_excel(compiled_df, pivot_df)

    st.download_button(
        label="⬇️ Download Compiled Data & Pivot Table (Excel)",
        data=excel_data,
        file_name="Compiled_Data_with_Pivot.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

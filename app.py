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

def csv_to_excel_bytes(csv_file):
    df = pd.read_csv(csv_file, dtype=str, engine='python', on_bad_lines='skip')
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

def read_file(file):
    if file.name.endswith(".csv"):
        excel_bytes = csv_to_excel_bytes(file)
        df = pd.read_excel(excel_bytes, dtype=str, header=0)
    else:
        df = pd.read_excel(file, dtype=str, header=0)
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('=', '', regex=False).str.replace('"', '', regex=False).str.strip()
    return df

def get_level(value):
    try:
        value = float(value)
        if value <= 249.99: return "Level1"
        elif value <= 1999.99: return "Level2"
        elif value <= 9999.99: return "Level3"
        elif value <= 24999.99: return "Level4"
        else: return "Level5"
    except:
        return None

if uploaded_files:
    dfs = [read_file(f) for f in uploaded_files]
    compiled_df = pd.concat(dfs, ignore_index=True).drop_duplicates(keep='first')

    # Remove unnamed columns
    compiled_df = compiled_df.loc[:, ~compiled_df.columns.str.contains('^Unnamed')]

    # Rename key columns (assuming EncounterID = A, FacilityCode = B, Balance = F)
    compiled_df.rename(columns={
        compiled_df.columns[0]: 'EncounterID',
        compiled_df.columns[1]: 'FacilityCode',
        compiled_df.columns[5]: 'Balance'
    }, inplace=True)

    # Convert Balance to numeric
    compiled_df['Balance_numeric'] = pd.to_numeric(compiled_df['Balance'].str.replace(',', '', regex=False), errors='coerce')

    # Apply Level
    compiled_df['Level'] = compiled_df['Balance_numeric'].apply(get_level)

    # Filter Age if exists
    if 'Age' in compiled_df.columns:
        compiled_df['Age'] = pd.to_numeric(compiled_df['Age'], errors='coerce')
        df_filtered = compiled_df[compiled_df['Age'] > 0]
    else:
        df_filtered = compiled_df

    # Sort by Balance descending
    compiled_df.sort_values(by='Balance_numeric', ascending=False, inplace=True)

    # Set EncounterID as index (row identifier)
    compiled_df.set_index('EncounterID', inplace=True)

    # Drop helper column for display
    compiled_df_display = compiled_df.drop(columns=['Balance_numeric'])

    # Display table
    st.subheader("📝 Compiled Data (Sorted by Balance, EncounterID as Index)")
    st.dataframe(compiled_df_display, use_container_width=True)

    # Pivot table
    pivot_data = []
    payer_col = 'CurrentPayer' if 'CurrentPayer' in compiled_df.columns else compiled_df.columns[1]
    for (payer, facility), group in df_filtered.groupby([payer_col, 'FacilityCode']):
        row = {"CurrentPayer": payer, "FacilityCode": facility}
        for lvl in ["Level5","Level4","Level3","Level2","Level1"]:
            lvl_group = group[group['Level']==lvl]
            row[f"{lvl}_Count"] = lvl_group['EncounterID'].count()
        row["Grand_Total_Count"] = group['EncounterID'].count()
        pivot_data.append(row)
    pivot_df = pd.DataFrame(pivot_data)

    st.subheader("📌 Pivot Table")
    st.dataframe(pivot_df, use_container_width=True)

    # Download Excel
    def to_excel(df_main, df_pivot):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_main.to_excel(writer, sheet_name='Compiled Data')
            df_pivot.to_excel(writer, sheet_name='Pivot Table', index=False)
        output.seek(0)
        return output.getvalue()

    excel_data = to_excel(compiled_df_display, pivot_df)

    st.download_button(
        "⬇️ Download Compiled Data & Pivot Table (Excel)",
        data=excel_data,
        file_name="Compiled_Data_with_Pivot.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

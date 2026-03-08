import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import time
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

# Page configuration
st.set_page_config(
    page_title="Telegram Bot Monitor",
    page_icon="🤖",
    layout="wide"
)

# Function to fetch data via SQLAlchemy
def get_data():
    try:
        # Building the connection string
        db_uri = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Create DB engine
        engine = create_engine(db_uri)
        
        # SQL query with Moscow timezone conversion (UTC+3)
        # We assume the server/DB defaults to UTC.
        # This converts the timestamp to 'Europe/Moscow' effectively.
        query = """
            SELECT 
                (event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow') as event_time, 
                event_type, 
                message_type, 
                description 
            FROM bot_logs 
            ORDER BY id DESC 
            LIMIT 50
        """
        
        # Read into Pandas
        df = pd.read_sql(query, engine)
        
        # Formatting for display: HH:MM:SS DD.MM.YYYY
        if not df.empty:
            df['event_time'] = pd.to_datetime(df['event_time']).dt.strftime('%H:%M:%S %d.%m.%Y')
        
        engine.dispose()
        return df
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

# --- INTERFACE ---

st.title("🤖 Bot Management Panel")

col1, col2 = st.columns(2)
with col1:
    st.write("Status: **🟢 Active**")
with col2:
    if st.button("🔄 Refresh Logs"):
        st.rerun()

st.divider()

st.subheader("📋 Real-time Activity Log (Moscow Time)")

df = get_data()

if not df.empty:
    def color_status(val):
        color = 'black'
        if val == 'RECEIVED': color = 'blue'
        elif val == 'SENT': color = 'green'
        elif val == 'ERROR': color = 'red'
        elif val == 'WARNING': color = 'orange'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        df.style.map(color_status, subset=['event_type']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No logs found or database is empty.")

# Auto-refresh every 10 seconds
time.sleep(10)
st.rerun()

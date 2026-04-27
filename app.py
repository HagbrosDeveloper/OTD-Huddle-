import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import datetime

# Attempt to import integrations
try:
    from streamlit_google_auth import Authenticate
    HAS_AUTH_LIB = True
except ImportError:
    HAS_AUTH_LIB = False

try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS_LIB = True
except ImportError:
    HAS_GSHEETS_LIB = False

# --- Page Config ---
st.set_page_config(
    page_title="Hagbros OTD Huddle",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { color: #f0f2f6; }
    div[data-testid="metric-container"] {
        background-color: #1e2127; border: 1px solid #4b4b4b;
        padding: 1rem; border-radius: 0.5rem;
    }
    .signature { color: #888888; font-size: 0.8rem; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

# --- Authentication Logic ---
st.session_state.setdefault('logged_in', False)
st.session_state.setdefault('user_name', 'Hagbros User')
st.session_state.setdefault('user_email', 'user@hagbros.com')

if HAS_AUTH_LIB and 'google_auth' in st.secrets:
    try:
        authenticator = Authenticate(
            secret_credentials_path='google_credentials.json', # Placeholder path
            cookie_name='hagbros_cookie',
            cookie_key='this_is_secret',
            redirect_uri='https://hagbros-otd.streamlit.app',
        )
        authenticator.check_authentification()
        if not st.session_state.get('connected'):
            st.title("🔒 Hagbros Employee Login")
            authenticator.login()
            st.stop() # Halt execution until logged in
        else:
            st.session_state.logged_in = True
            st.session_state.user_name = st.session_state['user_info'].get('name', 'Hagbros User')
            st.session_state.user_email = st.session_state['user_info'].get('email', '')
            
            with st.sidebar:
                st.write(f"Logged in as: **{st.session_state.user_name}**")
                authenticator.logout()
                st.markdown("---")
    except Exception as e:
        st.sidebar.warning("OAuth configuration incomplete. Running in Development mode.")
else:
    st.sidebar.warning("Auth bypassed (Dev Mode). Configure st.secrets to enable Google Login.")
    st.session_state.logged_in = True

# --- Database Logic (Google Sheets) ---
def load_comments():
    if HAS_GSHEETS_LIB and 'connections' in st.secrets:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            return conn.read(worksheet="Comments", usecols=[0, 1, 2]) # Assuming RefID, Comment, Signature
        except Exception as e:
            pass
    # Fallback to session state if DB isn't setup
    if 'mock_db' not in st.session_state:
        st.session_state.mock_db = pd.DataFrame(columns=["RefID", "Comment", "Signature"])
    return st.session_state.mock_db

def save_comment(ref_id, comment_text):
    signature = f" — {st.session_state.user_name}, {datetime.datetime.now().strftime('%b %d')}"
    new_row = pd.DataFrame([{"RefID": str(ref_id), "Comment": comment_text, "Signature": signature}])
    
    if HAS_GSHEETS_LIB and 'connections' in st.secrets:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            existing_df = conn.read(worksheet="Comments", usecols=[0, 1, 2])
            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            conn.update(worksheet="Comments", data=updated_df)
            return
        except Exception as e:
            st.error(f"Failed to save to Google Sheets: {e}")
            
    # Fallback
    st.session_state.mock_db = pd.concat([st.session_state.mock_db, new_row], ignore_index=True)

comments_db = load_comments()

# --- Client-Side Timer Component ---
def render_timer():
    html_code = """
    <div id="timer-container" style="text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white;">
        <h1 id="timer" style="font-size: 3.5rem; margin: 0; font-weight: bold;">15:00</h1>
        <button id="start-btn" style="margin-top: 15px; width: 100%; padding: 12px 20px; font-size: 1.1rem; font-weight: bold; cursor: pointer; background-color: #ff4b4b; color: white; border: none; border-radius: 5px;">Start Meeting</button>
    </div>
    <script>
        let timeLeft = 15 * 60; let timerId = null;
        const timerDisplay = document.getElementById('timer');
        const startBtn = document.getElementById('start-btn');
        function updateDisplay() {
            const mins = Math.floor(timeLeft / 60); const secs = timeLeft % 60;
            timerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            if (timeLeft < 3 * 60) { timerDisplay.style.color = '#ff4b4b'; } else { timerDisplay.style.color = '#00FF00'; }
        }
        startBtn.addEventListener('click', () => {
            if (timerId !== null) return; startBtn.disabled = true; startBtn.style.backgroundColor = '#555'; startBtn.textContent = "Meeting in Progress";
            timerId = setInterval(() => {
                if (timeLeft > 0) { timeLeft--; updateDisplay(); } else { clearInterval(timerId); timerDisplay.textContent = "TIME'S UP!"; timerDisplay.style.color = '#ff4b4b'; }
            }, 1000);
        });
        updateDisplay();
    </script>
    """
    components.html(html_code, height=160)

# --- Initialize Global Session State ---
if 'df_loading' not in st.session_state: st.session_state.df_loading = None
if 'df_backlog' not in st.session_state: st.session_state.df_backlog = None
if 'df_scrap' not in st.session_state: st.session_state.df_scrap = None

# --- Sidebar ---
with st.sidebar:
    st.header("⏱️ The Timeboxer")
    render_timer()
    st.markdown("---")
    st.header("Navigation")
    tabs = ["JobBoss2 Data Center", "Previous Day's Ship List", "Today's Ship List", "Scrap Review", "Machine Status", "Stalled Jobs", "Leads Issues", "Program Manager Issues"]
    selected_tab = st.radio("Go to:", tabs, index=0)

st.title(f"{selected_tab}")

# =====================================================================
# TAB: JOBBOSS2 DATA CENTER
# =====================================================================
if selected_tab == "JobBoss2 Data Center":
    st.markdown("### 📥 Centralized Report Uploads")
    st.write("Upload your JobBoss2 reports here before the meeting begins.")
    col1, col2, col3 = st.columns(3)
    with col1:
        file_loading = st.file_uploader("1. Loading Summary - Dept View", type=["csv"], key="load")
        if file_loading: st.session_state.df_loading = pd.read_csv(file_loading)
        if st.session_state.df_loading is not None: st.success("✅ Loaded!")
    with col2:
        file_backlog = st.file_uploader("2. Backlog Summary Report", type=["csv"], key="backlog")
        if file_backlog: st.session_state.df_backlog = pd.read_csv(file_backlog)
        if st.session_state.df_backlog is not None: st.success("✅ Loaded!")
    with col3:
        file_scrap = st.file_uploader("3. Cost Of Scrap Summary", type=["csv"], key="scrap")
        if file_scrap: st.session_state.df_scrap = pd.read_csv(file_scrap)
        if st.session_state.df_scrap is not None: st.success("✅ Loaded!")

# =====================================================================
# TAB: STALLED JOBS
# =====================================================================
elif selected_tab == "Stalled Jobs":
    st.markdown("### 🛑 Identify and Resolve Roadblocks to OTD")
    
    if st.session_state.df_loading is None:
        st.warning("⚠️ Please upload the **Loading Summary** report in the **JobBoss2 Data Center** tab first!")
    else:
        # Smart Logic Controls
        col1, col2 = st.columns(2)
        with col1:
            days_stalled_threshold = st.slider("Define Stalled (Days behind schedule):", min_value=1, max_value=90, value=3)
        with col2:
            newly_stalled_only = st.checkbox("🔥 Focus Mode: Only show jobs that stalled recently", value=False)
            if newly_stalled_only:
                recent_days = st.number_input("Became stalled in the last X days:", min_value=1, max_value=30, value=3)
            else:
                recent_days = 999 # effectively disabled
                
        st.markdown("---")
        
        try:
            df = st.session_state.df_loading.copy()
            df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce')
            df = df.dropna(subset=['StartDate'])
            
            today = pd.to_datetime('today').normalize()
            df['DaysBehindSchedule'] = (today - df['StartDate']).dt.days
            
            # Merge Customer Name and Date Entered from Backlog
            if st.session_state.df_backlog is not None:
                df_bl = st.session_state.df_backlog.copy()
                cust_col = next((c for c in df_bl.columns if 'customer' in c.lower()), None)
                date_col = next((c for c in df_bl.columns if 'date' in c.lower() and 'enter' in c.lower()), None)
                job_col = next((c for c in df_bl.columns if 'job' in c.lower() and 'number' in c.lower()), None)
                
                if job_col:
                    df['JobNumber_clean'] = df['JobNumber'].astype(str).str.strip().str.upper()
                    df_bl['JobNumber_clean'] = df_bl[job_col].astype(str).str.strip().str.upper()
                    
                    cols_to_merge = ['JobNumber_clean']
                    if cust_col: cols_to_merge.append(cust_col)
                    if date_col: cols_to_merge.append(date_col)
                        
                    df = df.merge(df_bl[cols_to_merge].drop_duplicates(subset=['JobNumber_clean']), on='JobNumber_clean', how='left')
                    
                    if cust_col: df.rename(columns={cust_col: 'Customer'}, inplace=True)
                    else: df['Customer'] = "N/A"
                    
                    if date_col: 
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%b %d, %Y')
                        df.rename(columns={date_col: 'Date Entered'}, inplace=True)
                    else: df['Date Entered'] = "N/A"
                    
                    df.drop(columns=['JobNumber_clean'], inplace=True)
            else:
                df['Customer'] = "(Upload Backlog)"
                df['Date Entered'] = "(Upload Backlog)"
            
            # Smart Filter Logic
            if newly_stalled_only:
                # E.g. Stalled threshold is 3. Recent days is 2. We only want jobs 3, 4, or 5 days behind.
                max_behind = days_stalled_threshold + recent_days
                filtered_df = df[(df['DaysBehindSchedule'] >= days_stalled_threshold) & (df['DaysBehindSchedule'] <= max_behind)].copy()
            else:
                filtered_df = df[df['DaysBehindSchedule'] >= days_stalled_threshold].copy()
                
            if filtered_df.empty:
                st.success("🎉 Great news! No jobs match this stall criteria.")
            else:
                # Format
                filtered_df['StartDate'] = filtered_df['StartDate'].dt.strftime('%b %d, %Y')
                filtered_df['JobNumber'] = filtered_df['JobNumber'].astype(str)
                filtered_df['DaysBehindSchedule'] = filtered_df['DaysBehindSchedule'].astype(int)
                
                display_cols = ['JobNumber', 'Customer', 'Date Entered', 'PartDescription', 'StepNo', 'WorkCenter', 'StartDate', 'DaysBehindSchedule', 'TotalHoursLeft']
                display_cols = [c for c in display_cols if c in filtered_df.columns]
                display_df = filtered_df[display_cols]
                
                def highlight_severe(val):
                    if isinstance(val, (int, float)) and val >= 30: return 'background-color: rgba(255, 0, 0, 0.4); color: white;' 
                    elif isinstance(val, (int, float)) and val >= 10: return 'background-color: rgba(255, 75, 75, 0.3); color: white;' 
                    elif isinstance(val, (int, float)) and val >= 5: return 'background-color: rgba(255, 165, 0, 0.3); color: white;' 
                    return ''

                # Note: Dataframes are 100% sortable by clicking headers in newer Streamlit versions, even with Styler
                styled_df = display_df.style.map(highlight_severe, subset=['DaysBehindSchedule'])
                st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)
                
        except Exception as e:
            st.error(f"🚨 An error occurred.")
            st.exception(e)

# =====================================================================
# TAB: SCRAP REVIEW
# =====================================================================
elif selected_tab == "Scrap Review":
    st.markdown("### 🗑️ Cost of Scrap Review & Root Cause Analysis")
    
    if st.session_state.df_scrap is None:
        st.warning("⚠️ Please upload the **Cost Of Scrap Summary** report in the **JobBoss2 Data Center** tab first!")
    else:
        try:
            scrap_df = st.session_state.df_scrap.copy()
            
            # Clean currency
            cost_cols = ['TotCostLB', 'TotMatCost', 'TotScrapCost', 'UnitCostScrap']
            for col in cost_cols:
                if col in scrap_df.columns:
                    scrap_df[col] = scrap_df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
            
            # Clean numbers (Round Good/Scrap to whole numbers)
            qty_cols = ['PcsGood', 'PcsScrap']
            for col in qty_cols:
                if col in scrap_df.columns:
                    scrap_df[col] = pd.to_numeric(scrap_df[col], errors='coerce').fillna(0).round(0).astype(int)
            
            if 'Date1' in scrap_df.columns:
                scrap_df['Date1'] = pd.to_datetime(scrap_df['Date1'], errors='coerce')
                min_dt = scrap_df['Date1'].min()
                max_dt = scrap_df['Date1'].max()
                
                # Date Filter Widget
                st.markdown("#### Filter by Date")
                selected_dates = st.date_input("Select Date Range:", value=[max_dt, max_dt], min_value=min_dt, max_value=max_dt)
                
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                    start_date = pd.to_datetime(start_date)
                    end_date = pd.to_datetime(end_date)
                    filtered_scrap = scrap_df[(scrap_df['Date1'] >= start_date) & (scrap_df['Date1'] <= end_date)].copy()
                else:
                    filtered_scrap = scrap_df.copy()
            else:
                filtered_scrap = scrap_df.copy()
            
            total_scrap_cost = filtered_scrap['TotScrapCost'].sum() if 'TotScrapCost' in filtered_scrap.columns else 0
            total_parts_scrapped = filtered_scrap['PcsScrap'].sum() if 'PcsScrap' in filtered_scrap.columns else 0
            
            col1, col2 = st.columns(2)
            with col1: st.metric("Total Scrap Cost (Filtered)", f"${total_scrap_cost:,.2f}")
            with col2: st.metric("Total Parts Scrapped (Filtered)", int(total_parts_scrapped))
                
            st.markdown("---")
            st.markdown("#### Detailed Scrap Log & Comments")
            
            display_cols = ['EmployeeDescription', 'Date1', 'JobNumber', 'PartNumber', 'WorkCenter', 'PcsGood', 'PcsScrap', 'TotScrapCost']
            display_cols = [c for c in display_cols if c in filtered_scrap.columns]
            
            disp_df = filtered_scrap[display_cols].copy()
            if 'Date1' in disp_df.columns: disp_df['Date1'] = disp_df['Date1'].dt.strftime('%b %d, %Y')
            if 'TotScrapCost' in disp_df.columns: disp_df = disp_df.sort_values('TotScrapCost', ascending=False)
            
            # Expanders for each scrap item to allow commenting
            for idx, row in disp_df.iterrows():
                job_num = row.get('JobNumber', 'Unknown')
                emp = row.get('EmployeeDescription', 'Unknown')
                cost = row.get('TotScrapCost', 0)
                
                with st.expander(f"🔴 {job_num} - {emp} - Scrap Cost: ${cost:,.2f}"):
                    cols = st.columns(len(display_cols))
                    for i, col_name in enumerate(display_cols):
                        cols[i].caption(col_name)
                        cols[i].write(row[col_name])
                    
                    st.markdown("##### Investigation Notes")
                    
                    # Display existing comments for this job
                    job_comments = comments_db[comments_db['RefID'] == str(job_num)]
                    if not job_comments.empty:
                        for _, c_row in job_comments.iterrows():
                            st.markdown(f"💬 {c_row['Comment']} <span class='signature'>{c_row['Signature']}</span>", unsafe_allow_html=True)
                    else:
                        st.write("*No notes yet. Add one below.*")
                    
                    # Add new comment
                    with st.form(key=f"form_{job_num}"):
                        new_note = st.text_input("Add a note (Root cause, corrective action, etc.)")
                        submit = st.form_submit_button("Save Note")
                        if submit and new_note:
                            save_comment(job_num, new_note)
                            st.rerun()

        except Exception as e:
            st.error("🚨 Error processing scrap data.")
            st.exception(e)

else:
    st.info(f"🚧 The **{selected_tab}** tab is currently under development.")

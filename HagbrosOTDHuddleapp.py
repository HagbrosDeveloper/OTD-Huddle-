import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import numpy as np

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
    /* Add some visual breathing room and distinct headers */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        color: #f0f2f6;
    }
    /* Style the metric cards slightly for better TV visibility */
    div[data-testid="metric-container"] {
        background-color: #1e2127;
        border: 1px solid #4b4b4b;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Client-Side Timer Component ---
def render_timer():
    html_code = """
    <div id="timer-container" style="text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white;">
        <h1 id="timer" style="font-size: 3.5rem; margin: 0; font-weight: bold;">15:00</h1>
        <button id="start-btn" style="margin-top: 15px; width: 100%; padding: 12px 20px; font-size: 1.1rem; font-weight: bold; cursor: pointer; background-color: #ff4b4b; color: white; border: none; border-radius: 5px;">Start Meeting</button>
    </div>
    <script>
        let timeLeft = 15 * 60;
        let timerId = null;
        
        const timerDisplay = document.getElementById('timer');
        const startBtn = document.getElementById('start-btn');
        
        function updateDisplay() {
            const mins = Math.floor(timeLeft / 60);
            const secs = timeLeft % 60;
            timerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            
            // Turn text red when under 3 minutes
            if (timeLeft < 3 * 60) {
                timerDisplay.style.color = '#ff4b4b'; 
            } else {
                timerDisplay.style.color = '#00FF00'; // bright green initially
            }
        }
        
        startBtn.addEventListener('click', () => {
            if (timerId !== null) return; // already running
            startBtn.disabled = true;
            startBtn.style.backgroundColor = '#555';
            startBtn.textContent = "Meeting in Progress";
            timerId = setInterval(() => {
                if (timeLeft > 0) {
                    timeLeft--;
                    updateDisplay();
                } else {
                    clearInterval(timerId);
                    timerDisplay.textContent = "TIME'S UP!";
                    timerDisplay.style.color = '#ff4b4b';
                }
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
    tabs = [
        "JobBoss2 Data Center", 
        "Previous Day's Ship List (OTD Review)",
        "Today's Ship List",
        "Previous Day's Scrap Review",
        "Machine Status",
        "Stalled Jobs",
        "Leads Issues",
        "Program Manager Issues"
    ]
    # Set default to Data Center so users initialize reports first
    selected_tab = st.radio("Go to:", tabs, index=0)

# --- Main Content Area ---
st.title(f"{selected_tab}")

# =====================================================================
# TAB: JOBBOSS2 DATA CENTER
# =====================================================================
if selected_tab == "JobBoss2 Data Center":
    st.markdown("### 📥 Centralized Report Uploads")
    st.write("Upload your JobBoss2 reports here before the meeting begins. The rest of the dashboard will automatically read from these files.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 1. Loading Summary")
        file_loading = st.file_uploader("Upload 'Loading Summary - Department View'", type=["csv"], key="load")
        if file_loading:
            st.session_state.df_loading = pd.read_csv(file_loading)
            st.success("✅ Loading Summary loaded!")
        elif st.session_state.df_loading is not None:
            st.success("✅ Loading Summary loaded in memory.")
            
    with col2:
        st.markdown("#### 2. Backlog Summary (Optional)")
        file_backlog = st.file_uploader("Upload 'Backlog Summary Report'", type=["csv"], key="backlog")
        if file_backlog:
            st.session_state.df_backlog = pd.read_csv(file_backlog)
            st.success("✅ Backlog Summary loaded!")
        elif st.session_state.df_backlog is not None:
            st.success("✅ Backlog Summary loaded in memory.")
            
    with col3:
        st.markdown("#### 3. Cost of Scrap (Optional)")
        file_scrap = st.file_uploader("Upload 'Cost Of Scrap Summary'", type=["csv"], key="scrap")
        if file_scrap:
            st.session_state.df_scrap = pd.read_csv(file_scrap)
            st.success("✅ Cost of Scrap loaded!")
        elif st.session_state.df_scrap is not None:
            st.success("✅ Cost of Scrap loaded in memory.")

# =====================================================================
# TAB: STALLED JOBS
# =====================================================================
elif selected_tab == "Stalled Jobs":
    st.markdown("### 🛑 Identify and Resolve Roadblocks to OTD")
    
    if st.session_state.df_loading is None:
        st.warning("⚠️ Please upload the **Loading Summary** report in the **JobBoss2 Data Center** tab first!")
    else:
        # Header controls (cleaner now that upload is gone)
        days_stalled_threshold = st.slider(
            "Define Stalled (Days behind schedule):",
            min_value=1,
            max_value=90,
            value=3,
            help="Filter jobs that are this many days behind their Scheduled Start Date."
        )
        st.markdown("---")
        
        try:
            df = st.session_state.df_loading.copy()
            
            # Check for required columns
            required_cols = ['JobNumber', 'PartDescription', 'StepNo', 'WorkCenter', 'StartDate', 'TotalHoursLeft']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Uploaded file is missing required columns: {', '.join(missing_cols)}")
            else:
                # Convert StartDate to datetime
                df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce')
                df = df.dropna(subset=['StartDate'])
                
                # Calculate DaysBehindSchedule
                today = pd.to_datetime('today').normalize()
                df['DaysBehindSchedule'] = (today - df['StartDate']).dt.days
                
                # -------------------------------------------------------------
                # Merge Data: Customer Name (from Backlog Summary)
                # -------------------------------------------------------------
                if st.session_state.df_backlog is not None:
                    df_bl = st.session_state.df_backlog.copy()
                    
                    # Dynamically find columns in Backlog since column names vary
                    cust_col = next((c for c in df_bl.columns if 'customer' in c.lower()), None)
                    job_col = next((c for c in df_bl.columns if 'job' in c.lower() and 'number' in c.lower()), None)
                    
                    if cust_col and job_col:
                        df['JobNumber_clean'] = df['JobNumber'].astype(str).str.strip().str.upper()
                        df_bl['JobNumber_clean'] = df_bl[job_col].astype(str).str.strip().str.upper()
                        
                        df = df.merge(df_bl[['JobNumber_clean', cust_col]].drop_duplicates(subset=['JobNumber_clean']), 
                                      on='JobNumber_clean', how='left')
                        df.rename(columns={cust_col: 'Customer'}, inplace=True)
                        df.drop(columns=['JobNumber_clean'], inplace=True)
                    else:
                        df['Customer'] = "Unknown"
                else:
                    df['Customer'] = "(Upload Backlog)"

                # -------------------------------------------------------------
                # Merge Data: Last Worker / Clock-In
                # Currently using Scrap Report as a proxy until Labor Report is added
                # -------------------------------------------------------------
                if st.session_state.df_scrap is not None:
                    df_scrap = st.session_state.df_scrap.copy()
                    
                    if 'EmployeeDescription' in df_scrap.columns and 'JobNumber' in df_scrap.columns:
                        df_scrap['JobNumber_clean'] = df_scrap['JobNumber'].astype(str).str.strip().str.upper()
                        df['JobNumber_clean'] = df['JobNumber'].astype(str).str.strip().str.upper()
                        
                        # Find the most recent date this job was touched (in the scrap report)
                        if 'Date1' in df_scrap.columns:
                            df_scrap['Date1'] = pd.to_datetime(df_scrap['Date1'], errors='coerce')
                            latest_touches = df_scrap.sort_values('Date1', ascending=False).drop_duplicates(subset=['JobNumber_clean'])
                        else:
                            latest_touches = df_scrap.drop_duplicates(subset=['JobNumber_clean'])
                            
                        # Merge the worker info
                        cols_to_merge = ['JobNumber_clean', 'EmployeeDescription']
                        if 'Date1' in df_scrap.columns: cols_to_merge.append('Date1')
                            
                        df = df.merge(latest_touches[cols_to_merge], on='JobNumber_clean', how='left')
                        df.rename(columns={'EmployeeDescription': 'Last Known Worker', 'Date1': 'Last Touch Date'}, inplace=True)
                        df.drop(columns=['JobNumber_clean'], inplace=True)
                
                # -------------------------------------------------------------
                # Filtering and Sorting
                # -------------------------------------------------------------
                filtered_df = df[df['DaysBehindSchedule'] >= days_stalled_threshold].copy()
                
                if filtered_df.empty:
                    st.success(f"🎉 Great news! No jobs are currently stalled by {days_stalled_threshold} or more days.")
                else:
                    # Sort Dataset so worst offenders are at the top
                    filtered_df = filtered_df.sort_values(by='DaysBehindSchedule', ascending=False)
                    
                    # Formatting for highly visible display
                    filtered_df['StartDate'] = filtered_df['StartDate'].dt.strftime('%b %d, %Y')
                    if 'Last Touch Date' in filtered_df.columns:
                        filtered_df['Last Touch Date'] = filtered_df['Last Touch Date'].dt.strftime('%b %d, %Y').fillna('N/A')
                    
                    filtered_df['JobNumber'] = filtered_df['JobNumber'].astype(str)
                    filtered_df['DaysBehindSchedule'] = filtered_df['DaysBehindSchedule'].astype(int)
                    
                    # Ensure specific data types
                    if 'Last Known Worker' in filtered_df.columns:
                        filtered_df['Last Known Worker'] = filtered_df['Last Known Worker'].fillna('N/A')
                    
                    # Dynamically select columns to display based on what data was provided
                    display_cols = ['JobNumber']
                    if 'Customer' in filtered_df.columns: display_cols.append('Customer')
                    display_cols.extend(['PartDescription', 'StepNo', 'WorkCenter', 'StartDate', 'DaysBehindSchedule', 'TotalHoursLeft'])
                    if 'Last Known Worker' in filtered_df.columns: display_cols.extend(['Last Known Worker', 'Last Touch Date'])
                    
                    display_df = filtered_df[display_cols]
                    
                    # Metrics
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric(label="Total Stalled Jobs", value=len(display_df))
                    with metric_col2:
                        worst_wc = display_df['WorkCenter'].value_counts().idxmax() if not display_df.empty else "N/A"
                        worst_wc_count = display_df['WorkCenter'].value_counts().max() if not display_df.empty else 0
                        st.metric(label="Worst Offending Work Center", value=worst_wc, delta=f"{worst_wc_count} bottlenecks", delta_color="inverse")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Visual styling
                    def highlight_severe(val):
                        # Extreme delays (30+ days) -> Dark Red
                        if isinstance(val, (int, float)) and val >= 30:
                            return 'background-color: rgba(255, 0, 0, 0.4); color: white;' 
                        # Moderate delays (10+ days) -> Light Red
                        elif isinstance(val, (int, float)) and val >= 10:
                            return 'background-color: rgba(255, 75, 75, 0.3); color: white;' 
                        # Warning delays (5+ days) -> Orange
                        elif isinstance(val, (int, float)) and val >= 5:
                            return 'background-color: rgba(255, 165, 0, 0.3); color: white;' 
                        return ''

                    # Apply styling
                    styled_df = display_df.style.map(highlight_severe, subset=['DaysBehindSchedule'])
                    
                    # Display Dataframe optimally for TV
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)
                    
        except Exception as e:
            st.error(f"🚨 An unexpected error occurred while processing the Stalled Jobs data.")
            st.exception(e)

# =====================================================================
# TAB: PREVIOUS DAY'S SCRAP REVIEW
# =====================================================================
elif selected_tab == "Previous Day's Scrap Review":
    st.markdown("### 🗑️ Cost of Scrap Review")
    
    if st.session_state.df_scrap is None:
        st.warning("⚠️ Please upload the **Cost Of Scrap Summary** report in the **JobBoss2 Data Center** tab first!")
    else:
        try:
            scrap_df = st.session_state.df_scrap.copy()
            
            # Clean currency columns
            cost_cols = ['TotCostLB', 'TotMatCost', 'TotScrapCost', 'UnitCostScrap']
            for col in cost_cols:
                if col in scrap_df.columns:
                    scrap_df[col] = scrap_df[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(float)
            
            # Format date
            if 'Date1' in scrap_df.columns:
                scrap_df['Date1'] = pd.to_datetime(scrap_df['Date1'], errors='coerce')
                max_date = scrap_df['Date1'].max()
                
                # Filter strictly for the most recent date to represent "Yesterday's Scrap"
                # (Assuming the report is run daily for the previous day)
                if not pd.isnull(max_date):
                    st.markdown(f"**Viewing Data For:** {max_date.strftime('%A, %B %d, %Y')}")
                    yesterdays_scrap = scrap_df[scrap_df['Date1'] == max_date].copy()
                else:
                    yesterdays_scrap = scrap_df.copy()
            else:
                yesterdays_scrap = scrap_df.copy()
            
            # High level metrics
            total_scrap_cost = yesterdays_scrap['TotScrapCost'].sum() if 'TotScrapCost' in yesterdays_scrap.columns else 0
            total_parts_scrapped = yesterdays_scrap['PcsScrap'].sum() if 'PcsScrap' in yesterdays_scrap.columns else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Scrap Cost (Reported)", f"${total_scrap_cost:,.2f}")
            with col2:
                st.metric("Total Parts Scrapped", int(total_parts_scrapped))
                
            st.markdown("---")
            
            # Display Columns
            display_cols = ['EmployeeCode', 'EmployeeDescription', 'JobNumber', 'PartNumber', 'WorkCenter', 'StepNo', 'PcsGood', 'PcsScrap', 'TotScrapCost', 'Comments']
            display_cols = [c for c in display_cols if c in yesterdays_scrap.columns]
            
            disp_df = yesterdays_scrap[display_cols].copy()
            
            # Sort by highest cost
            if 'TotScrapCost' in disp_df.columns:
                disp_df = disp_df.sort_values('TotScrapCost', ascending=False)
            
            # Highlighting expensive scrap
            def highlight_cost(val):
                if isinstance(val, (int, float)) and val > 100:
                    return 'background-color: rgba(255, 75, 75, 0.3); color: white;' # highlight items > $100
                return ''
                
            if 'TotScrapCost' in disp_df.columns:
                disp_styled = disp_df.style.format({'TotScrapCost': '${:,.2f}'}).map(highlight_cost, subset=['TotScrapCost'])
            else:
                disp_styled = disp_df
                
            st.dataframe(disp_styled, use_container_width=True, hide_index=True, height=500)
            
        except Exception as e:
            st.error("🚨 Error processing scrap data.")
            st.exception(e)

# =====================================================================
# TAB: OTHER (PLACEHOLDERS)
# =====================================================================
else:
    st.info(f"🚧 The **{selected_tab}** tab is currently under development.")

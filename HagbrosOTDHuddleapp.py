import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

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
# We use a JS component so the timer updates live without forcing Streamlit to re-run the entire Python script every second.
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

# --- Sidebar ---
with st.sidebar:
    st.header("⏱️ The Timeboxer")
    render_timer()
    
    st.markdown("---")
    st.header("Navigation")
    tabs = [
        "Previous Day's Ship List (OTD Review)",
        "Today's Ship List",
        "Previous Day's Scrap Review",
        "Machine Status",
        "Stalled Jobs",
        "Leads Issues",
        "Program Manager Issues"
    ]
    # Set default index to 4 ("Stalled Jobs") since it's the active one
    selected_tab = st.radio("Go to:", tabs, index=4)

# --- Main Content Area ---
st.title(f"{selected_tab}")

if selected_tab == "Stalled Jobs":
    st.markdown("### 🛑 Identify and Resolve Roadblocks to OTD")
    
    # Header controls
    col1, col2 = st.columns([1, 2])
    with col1:
        days_stalled_threshold = st.slider(
            "Define Stalled (Days behind schedule):",
            min_value=1,
            max_value=30,
            value=3,
            help="Filter jobs that are this many days behind their Scheduled Start Date."
        )
    with col2:
        uploaded_file = st.file_uploader("Upload 'Loading Summary - Department View.csv'", type=["csv"])
        
    st.markdown("---")
        
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Check for required columns to prevent unhandled KeyError
            required_cols = ['JobNumber', 'PartDescription', 'StepNo', 'WorkCenter', 'StartDate', 'TotalHoursLeft']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Uploaded file is missing required columns: {', '.join(missing_cols)}")
                st.info("Please ensure you are uploading the correct 'Loading Summary - Department View.csv' file.")
            else:
                # Process Data
                # Convert StartDate to datetime, coercing errors to NaT
                df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce')
                
                # Check if there were any parsing issues
                if df['StartDate'].isnull().any():
                    st.warning(f"⚠️ {df['StartDate'].isnull().sum()} rows had invalid StartDate formats and were excluded from this analysis.")
                    df = df.dropna(subset=['StartDate'])
                
                # Calculate DaysBehindSchedule
                today = pd.to_datetime('today').normalize()
                df['DaysBehindSchedule'] = (today - df['StartDate']).dt.days
                
                # Filter Dataset
                filtered_df = df[df['DaysBehindSchedule'] >= days_stalled_threshold].copy()
                
                if filtered_df.empty:
                    st.success(f"🎉 Great news! No jobs are currently stalled by {days_stalled_threshold} or more days.")
                    st.balloons()
                else:
                    # Sort Dataset so worst offenders are at the top
                    filtered_df = filtered_df.sort_values(by='DaysBehindSchedule', ascending=False)
                    
                    # Formatting for display
                    filtered_df['StartDate'] = filtered_df['StartDate'].dt.strftime('%Y-%m-%d')
                    
                    # Ensure specific data types for better dataframe display
                    filtered_df['JobNumber'] = filtered_df['JobNumber'].astype(str)
                    filtered_df['StepNo'] = filtered_df['StepNo'].astype(str)
                    filtered_df['DaysBehindSchedule'] = filtered_df['DaysBehindSchedule'].astype(int)
                    
                    # Filter Columns for Cross-Functional Readability
                    display_cols = ['JobNumber', 'PartDescription', 'StepNo', 'WorkCenter', 'StartDate', 'DaysBehindSchedule', 'TotalHoursLeft']
                    display_df = filtered_df[display_cols]
                    
                    # Metrics
                    metric_col1, metric_col2 = st.columns(2)
                    total_stalled = len(display_df)
                    
                    if not display_df.empty:
                        worst_wc = display_df['WorkCenter'].value_counts().idxmax()
                        worst_wc_count = display_df['WorkCenter'].value_counts().max()
                    else:
                        worst_wc = "N/A"
                        worst_wc_count = 0
                        
                    with metric_col1:
                        st.metric(label="Total Stalled Jobs", value=total_stalled)
                    with metric_col2:
                        st.metric(label="Worst Offending Work Center", value=worst_wc, delta=f"{worst_wc_count} bottlenecks", delta_color="inverse")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Visual styling for the dataframe
                    def highlight_severe(val):
                        # Highlight rows with extreme delays (e.g., >= 10 days)
                        if isinstance(val, (int, float)):
                            if val >= 10:
                                return 'background-color: rgba(255, 75, 75, 0.3); color: white;' # Streamlit red tint
                            elif val >= 5:
                                return 'background-color: rgba(255, 165, 0, 0.3); color: white;' # Orange tint
                        return ''

                    # Apply styling specifically to DaysBehindSchedule
                    styled_df = display_df.style.map(highlight_severe, subset=['DaysBehindSchedule'])
                    
                    # Display Dataframe optimally for TV
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True,
                        height=600 # Make it tall so it fills the screen
                    )
                    
        except pd.errors.EmptyDataError:
            st.error("🚨 The uploaded CSV file is empty.")
        except Exception as e:
            st.error(f"🚨 An unexpected error occurred while processing the file.")
            st.exception(e)
            
    else:
        # Placeholder view when no file is uploaded
        st.info("👆 Please upload the 'Loading Summary - Department View.csv' file using the uploader above.")
        
        # Display a mock visual so the monitor isn't just blank while waiting
        st.markdown("""
            <div style='opacity: 0.3; pointer-events: none; margin-top: 2rem;'>
                <h3>Example Stalled Jobs View</h3>
                <p>Data will appear here once the CSV is uploaded...</p>
                <hr>
            </div>
        """, unsafe_allow_html=True)

else:
    # Placeholder for other tabs
    st.info(f"🚧 The **{selected_tab}** tab is currently under development.")
    st.write("Please select 'Stalled Jobs' from the sidebar to view active features.")

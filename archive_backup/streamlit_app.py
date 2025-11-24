import streamlit as st
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from order_persistence import OrderStorage

st.set_page_config(layout="wide", page_title="MWE Explorer + Staff Log")

st.title("📊 MWE + Order & Staff Assistant Dashboard")

# ----------------- Turn Controls -----------------
turn = st.sidebar.number_input("Turn", min_value=0, value=0)
order_file = f"orders_turn{turn}.json"
log_file = f"staff_log_turn{turn}.json"

# ----------------- Orders Viewer -----------------
st.sidebar.title("📋 Orders Viewer")

if os.path.exists(order_file):
    orders = OrderStorage(order_file).load()
    df_orders = pd.DataFrame([o.to_dict() for o in orders])
    st.sidebar.markdown(f"🧾 Loaded {len(orders)} orders")
    order_status = st.sidebar.selectbox("Filter Orders by Status", ["All", "pending", "complete", "blocked"])
    if order_status != "All":
        df_orders = df_orders[df_orders["status"] == order_status]
    st.sidebar.dataframe(df_orders[["unit_id", "action", "status", "priority", "reason"]])
else:
    st.sidebar.info("No order file found.")

# ----------------- Staff Log Viewer -----------------
st.sidebar.title("🧠 Staff Assistant Log")

if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8") as f:
        log_data = json.load(f)
    df_log = pd.DataFrame(log_data)
    st.sidebar.markdown(f"📖 {len(df_log)} logged staff decisions")

    log_filter = st.sidebar.selectbox("Filter Log by Decision", ["All", "approved", "rejected"])
    if log_filter != "All":
        df_log = df_log[df_log["decision"] == log_filter]

    st.sidebar.dataframe(df_log[["unit", "action", "decision", "priority", "reason"]])
else:
    st.sidebar.info("No staff log found.")

# ----------------- Summary Upload Section -----------------
uploaded_file = st.file_uploader("Upload a summary JSON file (MWE or master_summary)", type="json")

if uploaded_file:
    data = json.load(uploaded_file)

    if "file_summaries" in data:
        st.header("📁 Master Summary")
        df = pd.DataFrame(data["file_summaries"])
        st.dataframe(df)

        fig, ax = plt.subplots()
        ax.bar(df["file"], df["total_spans"])
        ax.set_title("Total MWEs per File")
        ax.set_ylabel("MWEs")
        st.pyplot(fig)

    elif "span_tokens" in data[0]:
        st.header("📄 MWE Results")

        df = pd.DataFrame(data)
        types = df["type"].unique().tolist()
        selected_type = st.selectbox("Filter by type", ["All"] + types)
        min_conf = st.slider("Minimum confidence", 0.0, 1.0, 0.0, 0.05)

        filtered = df[
            (df["confidence"] >= min_conf) &
            ((df["type"] == selected_type) if selected_type != "All" else True)
        ]

        st.metric("Total MWEs", len(filtered))
        st.metric("Avg. Confidence", round(filtered["confidence"].mean(), 2) if not filtered.empty else 0)

        col1, col2 = st.columns(2)
        with col1:
            fig, ax = plt.subplots()
            ax.hist(filtered["confidence"], bins=10, color="skyblue")
            ax.set_title("Confidence Distribution")
            st.pyplot(fig)

        with col2:
            pie_data = filtered["type"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(pie_data, labels=pie_data.index, autopct="%1.1f%%")
            ax.set_title("Type Distribution")
            st.pyplot(fig)

        for _, row in filtered.iterrows():
            st.markdown(f"<div style='background:#f9f9f9;padding:8px;margin:5px;border-left:5px solid #ccc'>"
                        f"<b>{row['type']}</b> – <i>{', '.join(row['span_tokens'])}</i> "
                        f"(Confidence: {row['confidence']})<br><span style='color:gray'>{row['sentence']}</span>"
                        f"</div>", unsafe_allow_html=True)

        st.download_button(
            "📥 Download as Excel",
            data=filtered.to_excel(index=False, engine="openpyxl"),
            file_name="mwe_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

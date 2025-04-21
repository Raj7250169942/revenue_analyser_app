import streamlit as st
import pandas as pd
import plotly.express as px

# --- Streamlit Setup ---
st.set_page_config(page_title="Customer Revenue Dashboard", layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["📋 Dashboard", "📊 Analytics"])

uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx"])


@st.cache_data
def load_data(file):
    df = pd.read_excel(file, skiprows=1)
    df.columns = df.columns.str.strip()

    # Attempt to auto-map if columns aren't exact
    expected_columns = {"Customer Name", "Sales", "Sales With Tax"}
    actual_columns = set(df.columns)

    # Smart remapping
    column_mapping = {}
    for col in df.columns:
        if col.lower() == "name":
            column_mapping[col] = "Customer Name"
        elif col.lower() == "sales":
            column_mapping[col] = "Sales"
        elif col.lower() == "sales with tax":
            column_mapping[col] = "Sales With Tax"

    df.rename(columns=column_mapping, inplace=True)

    # Now validate
    if set(df.columns) != expected_columns:
        st.error("❌ The file format is not correct. Please upload a file with columns: 'Customer Name', 'Sales', and 'Sales With Tax'.")
        st.stop()

    # Clean numeric data
    for col in ["Sales", "Sales With Tax"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace("₹", "").str.replace(",", ""),
            errors="coerce"
        )

    df = df[df["Customer Name"].notna()]
    df = df[df["Customer Name"].str.lower() != "total"]
    return df


if uploaded_file:
    df = load_data(uploaded_file)

    if df is not None:
        if page == "📋 Dashboard":
            st.title("📊 Customer Revenue Dashboard")

            st.subheader("📋 Raw Data Preview")
            st.dataframe(df)

            st.metric("💰 Total Revenue (with Tax)",
                      f"₹ {df['Sales With Tax'].sum():,.2f}")
            st.metric("👥 Total Customers", df["Customer Name"].nunique())
            st.metric("📊 Avg. Revenue per Customer",
                      f"₹ {df['Sales With Tax'].mean():,.2f}")

            st.subheader("🔝 Top 20 Customers by Revenue")
            top_20 = df.sort_values("Sales With Tax",
                                    ascending=False).head(20)
            fig_top20 = px.bar(
                top_20,
                x="Sales With Tax",
                y="Customer Name",
                orientation="h",
                title="Top 20 Customers by Revenue",
            )
            fig_top20.update_layout(
                height=900,
                yaxis=dict(autorange="reversed"),
                margin=dict(l=180, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_top20, use_container_width=True)

            st.markdown("### 📈 Revenue by Customer (Paginated Scrollable View)")
            scroll_df = df.sort_values("Sales With Tax", ascending=False)
            customers_per_page = 20
            total_pages = (len(scroll_df) + customers_per_page - 1) // customers_per_page
            page_num = st.number_input("Page", min_value=1, max_value=total_pages, step=1)

            start_idx = (page_num - 1) * customers_per_page
            end_idx = start_idx + customers_per_page
            paginated_df = scroll_df.iloc[start_idx:end_idx]

            fig_scroll = px.bar(
                paginated_df,
                x="Sales With Tax",
                y="Customer Name",
                orientation='h',
                title=f"Customers {start_idx + 1} to {min(end_idx, len(scroll_df))} of {len(scroll_df)}"
            )

            fig_scroll.update_layout(
                yaxis=dict(automargin=True),
                xaxis_title="Revenue (₹)",
                yaxis_title=None,
                margin=dict(l=180, r=20, t=30, b=30),
                height=800,
                bargap=0.3,
                plot_bgcolor='white',
            )

            st.plotly_chart(fig_scroll, use_container_width=True)

        elif page == "📊 Analytics":
            st.title("📈 Customer Analytics")

            # ABC Segmentation
            st.subheader("🔎 ABC Customer Segmentation")
            df_sorted = df.sort_values("Sales With Tax", ascending=False).copy()
            df_sorted["Cumulative %"] = df_sorted["Sales With Tax"].cumsum() / df_sorted["Sales With Tax"].sum() * 100

            def classify(row):
                if row["Cumulative %"] <= 80:
                    return "A"
                elif row["Cumulative %"] <= 95:
                    return "B"
                else:
                    return "C"

            df_sorted["Segment"] = df_sorted.apply(classify, axis=1)
            st.dataframe(df_sorted[["Customer Name", "Sales With Tax", "Cumulative %", "Segment"]])

            st.subheader("📊 Customer Segments Distribution")
            segment_count = df_sorted["Segment"].value_counts()
            st.bar_chart(segment_count)

            # Segment Filter
            st.subheader("🎯 Segment Drill-Down")
            selected_segment = st.selectbox("Select Segment", options=["All", "A", "B", "C"])
            if selected_segment != "All":
                segment_df = df_sorted[df_sorted["Segment"] == selected_segment]
                st.write(f"📋 {len(segment_df)} customers in Segment **{selected_segment}**")
                st.dataframe(segment_df)
            else:
                st.info("Showing all segments. Select A/B/C to filter.")

            # Pareto Chart
            st.subheader("📐 Pareto Analysis (80/20 Rule)")
            pareto_df = df_sorted.copy()
            fig_pareto = px.bar(
                pareto_df,
                x="Customer Name",
                y="Sales With Tax",
                title="Pareto Chart: Revenue by Customer",
            )
            fig_pareto.add_scatter(
                x=pareto_df["Customer Name"],
                y=pareto_df["Cumulative %"],
                mode="lines+markers",
                name="Cumulative %",
                yaxis="y2"
            )
            fig_pareto.update_layout(
                yaxis=dict(title="Sales With Tax"),
                yaxis2=dict(
                    overlaying="y",
                    side="right",
                    title="Cumulative %",
                    range=[0, 100]
                ),
                height=600
            )
            st.plotly_chart(fig_pareto, use_container_width=True)

            # Outlier Detection
            st.subheader("🚨 Outlier Detection & Exception Reporting")

            low_revenue_threshold = st.slider("Set Low Revenue Threshold (₹)", min_value=0, max_value=100000, value=5000)
            high_revenue_spike_threshold = st.slider("Set Revenue Spike Threshold (₹)", min_value=100000, max_value=1000000, value=300000)

            low_revenue_customers = df[df["Sales With Tax"] < low_revenue_threshold]
            high_spike_customers = df[df["Sales With Tax"] > high_revenue_spike_threshold]

            st.markdown("#### 🧊 Customers with Very Low Revenue (Possible Churn)")
            if not low_revenue_customers.empty:
                st.dataframe(low_revenue_customers[["Customer Name", "Sales With Tax"]])
            else:
                st.success("No low-revenue customers found 👌")

            st.markdown("#### 🚀 Customers with Unusually High Revenue (Spikes to Review)")
            if not high_spike_customers.empty:
                st.dataframe(high_spike_customers[["Customer Name", "Sales With Tax"]])
            else:
                st.success("No significant revenue spikes detected 🙌")

            # Download
            st.subheader("📥 Download Cleaned Data")
            st.download_button("Download as CSV", df.to_csv(index=False), "cleaned_revenue_data.csv")

else:
    st.info("⬆️ Please upload your Excel file using the sidebar to begin.")

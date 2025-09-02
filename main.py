import streamlit as st
import pandas as pd
from scraper import CurrencyRateScraper
import time

def main():
    st.title("Currency Exchange Rates - Live Data")
    st.markdown("CashChanger Singapore rates **multiplied** by Grand Superrich SGD buying rate + SGD 100 note pricing")
    
    # Initialize scraper
    scraper = CurrencyRateScraper()
    
    # Add refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Rates"):
            st.rerun()
    
    with col2:
        st.markdown(f"*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
    
    # Show loading spinner
    with st.spinner("Fetching currency rates from CashChanger Singapore..."):
        # Get CashChanger data
        cashchanger_data = scraper.scrape_cashchanger()
        # print(cashchanger_data)
    
    # Also fetch Singapore 100 note pricing from Grand Superrich
    with st.spinner("Fetching Singapore 100 note pricing from Grand Superrich..."):
        superrich_data = scraper.scrape_grandsuperrich_sgd100()
    
    # Combine all data
    all_data = []
    grand_sgd_buy_rate = None
    
    if superrich_data is not None and not superrich_data.empty:
        st.success("Successfully fetched Singapore 100 note pricing from Grand Superrich!")
        
        # Get the SGD buying rate from Grand Superrich to use as multiplier
        for _, row in superrich_data.iterrows():
            if 'SGD' in row['Currency']:
                grand_sgd_buy_rate = row['Buy Rate']
                st.info(f"Using Grand Superrich SGD buying rate: {grand_sgd_buy_rate}")
                break
    
    if cashchanger_data is not None and not cashchanger_data.empty:
        st.success("Successfully fetched currency rates from CashChanger!")
        
        # Add CashChanger rates multiplied by Grand Superrich SGD rate
        for _, row in cashchanger_data.iterrows():
            if grand_sgd_buy_rate is not None:
                # Multiply CashChanger rate with Grand Superrich SGD buying rate
                multiplied_rate = row['Buy Rate'] * grand_sgd_buy_rate
                all_data.append({
                    'Codes': row['Currency'],
                    'rates': multiplied_rate
                })
            else:
                # Use original rate if no Grand Superrich rate available
                all_data.append({
                    'Codes': row['Currency'],
                    'rates': row['Buy Rate']
                })
    
    if superrich_data is not None and not superrich_data.empty:
        # Add Grand Superrich SGD rate for reference
        for _, row in superrich_data.iterrows():
            all_data.append({
                'Codes': row['Currency'],
                'rates': row['Buy Rate']
            })
    
    if all_data:
        # Create DataFrame for display
        display_df = pd.DataFrame(all_data)
        
        # Display the table
        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True
        )
        
        # Show summary
        st.markdown(f"**Total rates displayed:** {len(display_df)}")
        
    else:
        st.error("Unable to fetch currency rates. Please try again.")
        st.markdown("**Note:** Make sure CashChanger Singapore is accessible.")

if __name__ == "__main__":
    main()

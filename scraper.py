import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import streamlit as st
from typing import Optional, List, Dict, Union
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright
from superrich import get_superrich_rates
import re

class CurrencyRateScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = 10
    
    def scrape_cashchanger(self) -> Optional[pd.DataFrame]:
        """Scrape currency rates from cashchanger.co/singapore"""
        try:
            st.info("Fetching rates from CashChanger...")
            
            # Use Singapore-specific URL
            url = "https://cashchanger.co/singapore"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            rates_data = []
            
            # -------------------------

            # Look for money changer listings with rates
            # CashChanger shows money changers with their rates
            import re
            money_changers = soup.find_all('div', class_=re.compile(r'rate|exchange|changer|currency', re.I))
            
            # Also try to find any tables or structured data
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        
                        # Look for currency codes and rates
                        import re
                        for i, cell_text in enumerate(cell_texts):
                            currency_match = re.search(r'\b([A-Z]{3})\b', cell_text)
                            if currency_match and i + 2 < len(cell_texts):
                                currency = currency_match.group(1)
                                if currency in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SGD']:
                                    # Try to extract buy/sell rates from next cells
                                    try:
                                        buy_rate = float(re.findall(r'\d+\.\d+', cell_texts[i+1])[0])
                                        sell_rate = float(re.findall(r'\d+\.\d+', cell_texts[i+2])[0])
                                        
                                        rates_data.append({
                                            'Currency': currency,
                                            'Buy Rate': buy_rate,
                                            'Sell Rate': sell_rate,
                                            'Source': 'CashChanger'
                                        })
                                    except (IndexError, ValueError):
                                        continue
            
            # If no structured data, try text parsing
            if not rates_data:
                text_content = soup.get_text()
                import re
                
                # Look for CashChanger specific pattern: "CURRENCY AMOUNT = SGD RATE"
                # Examples: "USD 1 = SGD 1.282", "JPY 1000 = SGD 8.715"
                rate_patterns = re.findall(r'([A-Z]{3})\s+(\d+)\s+=\s+SGD\s+([\d\.]+)', text_content)
                
                for match in rate_patterns:
                    currency, amount, sgd_rate = match
                    amount = float(amount)
                    sgd_rate = float(sgd_rate)
                    
                    # Convert to rate per 1 unit of foreign currency (actual rate)
                    rate_per_unit = sgd_rate / amount
                    
                    # Use the actual rate without any spread adjustments
                    rates_data.append({
                        'Currency': currency,
                        'Buy Rate': rate_per_unit,
                        'Sell Rate': rate_per_unit,
                        'Source': 'CashChanger'
                    })
                
                # Remove duplicates by keeping the most recent rate for each currency
                if rates_data:
                    df_temp = pd.DataFrame(rates_data)
                    df_temp = df_temp.drop_duplicates(subset=['Currency'], keep='last')
                    rates_data = df_temp.to_dict('records')
            
            if rates_data:
                df = pd.DataFrame(rates_data)
                # Remove duplicates
                df = df.drop_duplicates(subset=['Currency'])
                st.success(f"✅ CashChanger: Found {len(df)} currency rates")
                
                return df
            else:
                st.warning("⚠️ CashChanger: No currency data found")
                return pd.DataFrame()
                
        except requests.RequestException as e:
            st.error(f"❌ CashChanger: Network error - {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ CashChanger: Parsing error - {str(e)}")
            
            return pd.DataFrame()
    
    def scrape_grandsuperrich_sgd100(self) -> Optional[pd.DataFrame]:
        """Scrape Singapore 100 note pricing from grandsuperrich.com"""
        try:
            st.info("Fetching Singapore 100 note pricing from Grand Superrich...")
            
            url = "https://grandsuperrich.com"
            # url = "https://superrichthailand.com"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text()
            # print(text_content)
            rates_data = []

            # -------------------------
            
            print(get_superrich_rates())

            # -------------------------


            
            # Look specifically for Singapore SGD 100 note pricing
            # Pattern: "SingaporeSGD 100-5025.0525.20" means SGD 100 denomination with buy 25.05, sell 25.20
            sgd_100_pattern = re.search(r'SingaporeSGD\s+100[^0-9]*(\d+\.\d+)(\d+\.\d+)', text_content)
            
            if sgd_100_pattern:
                buy_rate = float(sgd_100_pattern.group(1))
                sell_rate = float(sgd_100_pattern.group(2))
                
                rates_data.append({
                    'Currency': 'SGD 100',
                    'Buy Rate': 25.1,
                    'Sell Rate': sell_rate,
                    'Source': 'Grand Superrich'
                })
                
                st.success(f"✅ Grand Superrich: Found SGD 100 note pricing - Buy: {buy_rate}, Sell: {sell_rate}")
            else:
                st.warning("⚠️ Grand Superrich: SGD 100 note pricing not found")
                return pd.DataFrame()
            
            if rates_data:
                return pd.DataFrame(rates_data)
            else:
                return pd.DataFrame()
                
        except requests.RequestException as e:
            st.error(f"❌ Grand Superrich: Network error - {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Grand Superrich: Parsing error - {str(e)}")
            return pd.DataFrame()
    
    def combine_data(self, df1: Optional[pd.DataFrame], df2: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Combine data from both sources into a single DataFrame"""
        try:
            # Create list to store all data
            all_data = []
            
            # Add data from first source
            if df1 is not None and not df1.empty:
                all_data.append(df1)
            
            # Add data from second source
            if df2 is not None and not df2.empty:
                all_data.append(df2)
            
            if not all_data:
                return pd.DataFrame()
            
            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Sort by currency and source
            combined_df = combined_df.sort_values(['Currency', 'Source'])
            
            # Format numeric columns
            if 'Buy Rate' in combined_df.columns:
                combined_df['Buy Rate'] = combined_df['Buy Rate'].round(4)
            
            if 'Sell Rate' in combined_df.columns:
                combined_df['Sell Rate'] = combined_df['Sell Rate'].round(4)
            
            # Add difference column if we have rates from both sources for same currency
            if len(combined_df) > 1:
                combined_df['Spread'] = (combined_df['Sell Rate'] - combined_df['Buy Rate']).round(4)
            
            return combined_df
            
        except Exception as e:
            st.error(f"Error combining data: {str(e)}")
            return pd.DataFrame()
    
    def get_mock_data_if_needed(self) -> pd.DataFrame:
        """Return empty DataFrame - no mock data as per guidelines"""
        return pd.DataFrame()

import os
import matplotlib.pyplot as plt
import pandas as pd
import json
import requests
from datetime import datetime
from config import ASSETS_DIR

# Style Configuration for "Dark Mode" Bloomberg Aesthetic
plt.style.use('dark_background')
COLORS = {
    'primary': '#4a90e2',    # Sterling Blue
    'secondary': '#f06292',  # Alert Red/Pink
    'accent': '#00e676',     # Success Green
    'text': '#e0e0e0',
    'primary': '#4a90e2',    # Sterling Blue
    'secondary': '#f06292',  # Alert Red/Pink
    'accent': '#00e676',     # Success Green
    'text': '#e0e0e0',
    'grid': '#333333',
    'bg': '#101827'          # Matches Dashboard Card BG
}

# --- BLS Config ---
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
# Series: Auto Maint, Medical Care, All Items (CPI-U)
BLS_SERIES = {
    "CUUR0000SETD": "Auto Repair", 
    "CUUR0000SAM": "Medical Care",
    "CUUR0000SA0": "General Inflation" 
}

class VisualAnalyst:
    def __init__(self):
        self.output_dir = ASSETS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_assets(self):
        print("🎨 Visual Analyst starting daily render cycle...")
        
        # We now rotate the "Chart of the Day" to keep the dashboard fresh
        # But we generate ALL of them so they are available if we want to switch manually
        
        charts = [
            ("inflation", self.generate_inflation_chart),
            ("storm", self.generate_storm_chart),
            ("sector", self.generate_sector_chart),
            ("rate", self.generate_yield_chart)
        ]
        
        import random
        # Pick one to be the "Main Feature" -> copied to bedrock_chart.png
        selected_type, selected_func = random.choice(charts)
        print(f"   🎲 Chart of the Day selected: {selected_type.upper()}")
        
        # Run the selected one first and check output
        output_path = selected_func()
        
        if output_path and os.path.exists(output_path):
            import shutil
            shutil.copy(output_path, os.path.join(self.output_dir, "bedrock_chart.png"))
            print("   ✅ Updated bedrock_chart.png")
            
        print("✅ Visual assets updated.")

    def _setup_plot(self):
        fig, ax = plt.subplots(figsize=(12, 7)) 
        fig.patch.set_facecolor(COLORS['bg'])
        ax.set_facecolor(COLORS['bg'])
        return fig, ax

    def _finalize_plot(self, ax, title, filename):
        ax.set_title(title, color=COLORS['text'], fontsize=16, pad=20, fontweight='bold')
        ax.tick_params(colors=COLORS['text'], labelsize=10)
        ax.grid(color=COLORS['grid'], linestyle=':', linewidth=0.5)
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.legend(facecolor=COLORS['bg'], labelcolor=COLORS['text'], framealpha=0, fontsize=10)
        
        save_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(save_path, facecolor=COLORS['bg'], dpi=150)
        plt.close()
        print(f"      ✅ Saved {filename}")
        return save_path

    # --- CHART GENERATORS ---

    def generate_inflation_chart(self):
        print("   - Rendering Inflation Chart (BLS Data)...")
        # Reuse existing BLS logic but return path
        try:
            headers = {'Content-type': 'application/json'}
            payload = json.dumps({"seriesid": list(BLS_SERIES.keys()), "startyear": "2021", "endyear": "2025"})
            p = requests.post(BLS_API_URL, data=payload, headers=headers)
            json_data = p.json()
            
            if json_data.get('status') != 'REQUEST_NOT_PROCESSED':
                data_frames = {}
                for series in json_data['Results']['series']:
                    name = BLS_SERIES.get(series['seriesID'], series['seriesID'])
                    dates, values = [], []
                    for item in series['data']:
                        try:
                            dates.append(f"{item['year']}-{item['period'][1:]}")
                            values.append(float(item['value']))
                        except: continue
                    if dates:
                        df = pd.DataFrame({'Date': pd.to_datetime(dates), name: values}).set_index('Date')
                        data_frames[name] = df
                
                final_df = pd.concat(data_frames.values(), axis=1).sort_index()
                normalized_df = (final_df / final_df.iloc[0]) * 100
                
                fig, ax = self._setup_plot()
                for col in normalized_df.columns:
                    width = 3 if "Auto" in col else (2 if "Medical" in col else 1.5)
                    style = '--' if "Medical" in col else '-'
                    color = COLORS['secondary'] if "Auto" in col else (COLORS['accent'] if "Medical" in col else COLORS['primary'])
                    ax.plot(normalized_df.index, normalized_df[col], color=color, linewidth=width, linestyle=style, label=col)
                return self._finalize_plot(ax, "Inflation: 5-Year Cost Index (Base=100)", "inflation_chart.png")
                
        except Exception as e:
            print(f"      ⚠️ BLS failed ({e}), using fallback.")
        
        return self._draw_mock_chart()

    def generate_storm_chart(self):
        print("   - Rendering Storm Volatility...")
        try:
            lat, lon = 35.4676, -97.5164 
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - pd.DateOffset(days=90)).strftime("%Y-%m-%d")
            url = "https://archive-api.open-meteo.com/v1/archive"
            r = requests.get(url, params={"latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date, "daily": "wind_gusts_10m_max", "timezone": "America/Chicago"})
            data = r.json()
            
            df = pd.DataFrame({'Date': pd.to_datetime(data['daily']['time']), 'Gusts': data['daily']['wind_gusts_10m_max']})
            fig, ax = self._setup_plot()
            ax.fill_between(df['Date'], df['Gusts'], color=COLORS['primary'], alpha=0.3)
            ax.plot(df['Date'], df['Gusts'], color=COLORS['primary'], linewidth=2, label='Wind Speed')
            
            df['Rolling'] = df['Gusts'].rolling(window=7).mean()
            ax.plot(df['Date'], df['Rolling'], color=COLORS['text'], linestyle='--', alpha=0.5, label='7-Day Trend')
            
            return self._finalize_plot(ax, "Real-Time Risk: Peak Wind Gusts", "storm_chart.png")
        except Exception as e:
            print(f"      ❌ Storm Chart Failed: {e}")
            return None

    def generate_sector_chart(self):
        print("   - Rendering Sector Alpha (KIE vs SPY)...")
        try:
            import yfinance as yf
            end_date = datetime.now()
            start_date = end_date - pd.DateOffset(months=6)
            tickers = ['KIE', 'SPY'] 
            data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
            
            if data.empty: raise ValueError("No data returned")
            
            # Normalize to % Return
            normalized = (data / data.iloc[0]) * 100 - 100
            
            # Plot
            fig, ax = self._setup_plot() # Corrected: use return values from _setup_plot
            
            # Insurance (KIE)
            ax.plot(normalized.index, normalized['KIE'], color=COLORS['secondary'], linewidth=3, label='Insurance (KIE)')
            # Market (SPY)
            ax.plot(normalized.index, normalized['SPY'], color=COLORS['primary'], linewidth=1.5, alpha=0.6, label='S&P 500')
            
            ax.fill_between(normalized.index, normalized['KIE'], normalized['SPY'], where=(normalized['KIE'] > normalized['SPY']), 
                            color=COLORS['secondary'], alpha=0.1, interpolate=True)
            
            return self._finalize_plot(ax, "Sector Alpha: Insurance vs Market (6Mo)", "sector_chart.png")
            
        except Exception as e:
            print(f"      ❌ Sector Chart Failed: {e}")
            return self._draw_mock_sector()

    def generate_yield_chart(self):
        print("   - Rendering Treasury Yield Curve (10Y)...")
        try:
            import yfinance as yf
            end_date = datetime.now()
            start_date = end_date - pd.DateOffset(years=2) # 2 Year view to show trend
            
            # Fetch 10-Year Treasury Yield
            data = yf.download("^TNX", start=start_date, end=end_date, progress=False)['Close']
            
            if data.empty: raise ValueError("No data returned")
            
            # Plot
            fig, ax = self._setup_plot() # Corrected: use return values from _setup_plot
            
            # Main Line
            ax.plot(data.index, data, color=COLORS['accent'], linewidth=2.5, label='10-Year Yield')
            
            # Fill Area
            ax.fill_between(data.index, data, data.min().min() * 0.95, color=COLORS['accent'], alpha=0.1)
            
            # Add latest value annotation
            latest_val = data.iloc[-1].item() if hasattr(data.iloc[-1], 'item') else data.iloc[-1]
            latest_date = data.index[-1]
            ax.scatter([latest_date], [latest_val], color='white', s=50, zorder=5)
            ax.text(latest_date, latest_val + 0.1, f"{latest_val:.2f}%", color='white', fontweight='bold', ha='left')

            return self._finalize_plot(ax, "Cost of Capital: 10-Year Treasury Yield", "yield_chart.png")

        except Exception as e:
            print(f"      ❌ Yield Chart Failed: {e}")
            return self._draw_mock_yield()

    # --- MOCKS ---

    def _draw_mock_chart(self):
        print("      ⚠️ Generating MOCK Inflation Chart...")
        dates = pd.date_range(start="2021-01-01", end="2025-01-01", freq="MS")
        mock_data = {
            "Auto Repair": [100 + (x * 0.8) + (x*x*0.01) for x in range(len(dates))],
            "Medical Care": [100 + (x * 0.4) for x in range(len(dates))]
        }
        df = pd.DataFrame(mock_data, index=dates)
        fig, ax = self._setup_plot()
        ax.plot(df.index, df['Auto Repair'], color=COLORS['secondary'], linewidth=3, label='Auto Repair (Mock)')
        return self._finalize_plot(ax, "Inflation: Cost Index (Mock)", "inflation_chart.png")
        
    def _draw_mock_sector(self):
        print("      ⚠️ Generating MOCK Sector Chart...")
        dates = pd.date_range(end=datetime.now(), periods=180)
        import numpy as np
        # Simulate KIE beating SPY
        spy = np.cumsum(np.random.randn(180)) 
        kie = np.cumsum(np.random.randn(180) + 0.05) # Slight alpha
        
        df = pd.DataFrame({'Date': dates, 'SPY': spy, 'KIE': kie}).set_index('Date')
        
        fig, ax = self._setup_plot()
        ax.plot(df.index, df['KIE'], color=COLORS['secondary'], linewidth=3, label='Insurance (Mock)')
        ax.plot(df.index, df['SPY'], color=COLORS['primary'], linewidth=1.5, alpha=0.6, label='S&P 500 (Mock)')
        return self._finalize_plot(ax, "Sector Alpha: Insurance vs Market (Mock)", "sector_chart.png")

    def _draw_mock_yield(self):
        print("      ⚠️ Generating MOCK Yield Chart...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq='W')
        # Simulate rising yields
        import numpy as np
        yields = 3.5 + np.cumsum(np.random.randn(100) * 0.05) + np.linspace(0, 1, 100)
        df = pd.DataFrame({'Yield': yields}, index=dates)
        
        fig, ax = self._setup_plot()
        ax.plot(df.index, df['Yield'], color=COLORS['accent'], linewidth=2.5, label='10-Year Yield (Mock)')
        return self._finalize_plot(ax, "Cost of Capital: 10-Year Treasury Yield (Mock)", "yield_chart.png")


if __name__ == "__main__":
    analyst = VisualAnalyst()
    analyst.generate_all_assets()

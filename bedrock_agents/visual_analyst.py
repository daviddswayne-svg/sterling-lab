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
        self.generate_inflation_chart()
        # self.generate_disaster_map() # Removed per user request
        self.generate_storm_chart()
        print("✅ Visual assets updated.")

    def generate_inflation_chart(self):
        print("   - Rendering Inflation Chart (BLS Data)...")
        headers = {'Content-type': 'application/json'}
        # Last 5 years = 2021-2025 (approx)
        payload = json.dumps({
            "seriesid": list(BLS_SERIES.keys()),
            "startyear": "2021",
            "endyear": "2025"
        })
        
        try:
            p = requests.post(BLS_API_URL, data=payload, headers=headers)
            json_data = p.json()
            
            if json_data['status'] == 'REQUEST_NOT_PROCESSED':
                print(f"      ⚠️ BLS Limit Reached or Error: {json_data['message'][0]}")
                # Use Mock Data if API fails
                self._draw_mock_chart()
                return

            # Process Data
            data_frames = {}
            for series in json_data['Results']['series']:
                series_id = series['seriesID']
                name = BLS_SERIES.get(series_id, series_id)
                
                dates = []
                values = []
                for item in series['data']:
                    try:
                        val = float(item['value'])
                        dates.append(f"{item['year']}-{item['period'][1:]}") # YYYY-MM
                        values.append(val)
                    except ValueError:
                        continue # Skip missing data points encoded as '-'
                
                if not dates: continue
                
                df = pd.DataFrame({'Date': pd.to_datetime(dates), name: values})
                df.set_index('Date', inplace=True)
                data_frames[name] = df
            
            # Combine
            final_df = pd.concat(data_frames.values(), axis=1).sort_index()
            # Normalize to 100 at start date for comparison
            normalized_df = (final_df / final_df.iloc[0]) * 100
            
            self._render_plot(normalized_df, "Why Rates Are Up: 5-Year Cost Index (Base=100)", "inflation_chart.png")
            
        except Exception as e:
            print(f"      ❌ BLS Fetch Failed: {e}")
            self._draw_mock_chart()

    def _render_plot(self, df, title, filename):
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(COLORS['bg'])
        ax.set_facecolor(COLORS['bg'])
        
        # Plot lines
        for col in df.columns:
            if "Auto" in col:
                ax.plot(df.index, df[col], color=COLORS['secondary'], linewidth=3, label=col)
            elif "Medical" in col:
                ax.plot(df.index, df[col], color=COLORS['accent'], linewidth=2, linestyle='--', label=col)
            else:
                ax.plot(df.index, df[col], color=COLORS['primary'], linewidth=1.5, alpha=0.7, label=col)
        
        # Styling
        ax.set_title(title, color=COLORS['text'], fontsize=14, pad=20, fontweight='bold')
        ax.tick_params(colors=COLORS['text'])
        ax.grid(color=COLORS['grid'], linestyle=':', linewidth=0.5)
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        ax.legend(facecolor=COLORS['bg'], labelcolor=COLORS['text'], framealpha=0)
        
        # Save
        save_path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(save_path, facecolor=COLORS['bg'], dpi=120)
        plt.close()
        print(f"      ✅ Saved {filename}")

    def _draw_mock_chart(self):
        print("      ⚠️ Generating MOCK Inflation Chart...")
        # Fallback if API fails
        dates = pd.date_range(start="2021-01-01", end="2025-01-01", freq="MS")
        mock_data = {
            "Auto Repair": [100 + (x * 0.8) + (x*x*0.01) for x in range(len(dates))], # Exponential growth
            "Medical Care": [100 + (x * 0.4) for x in range(len(dates))], # Linear
            "General Inflation": [100 + (x * 0.3) for x in range(len(dates))] # Slower linear
        }
        df = pd.DataFrame(mock_data, index=dates)
        self._render_plot(df, "Why Rates Are Up: 5-Year Cost Index (MOCK)", "inflation_chart.png")

    # REMOVED: generate_disaster_map (User requested removal)

    def generate_storm_chart(self):
        print("   - Rendering Storm Volatility (Open-Meteo Real Data)...")
        # Replacing simulated NOAA data with Real Open-Meteo Data (Free, No Key)
        # Using Oklahoma City (Tornado Alley) as a proxy for "Severe Weather Risk"
        lat, lon = 35.4676, -97.5164 
        
        # Get data for the last 90 days
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - pd.DateOffset(days=90)).strftime("%Y-%m-%d")
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "wind_gusts_10m_max", # Key metric for storm damage
            "timezone": "America/Chicago"
        }
        
        try:
            r = requests.get(url, params=params)
            data = r.json()
            
            dates = data['daily']['time']
            gusts = data['daily']['wind_gusts_10m_max']
            
            df = pd.DataFrame({'Date': pd.to_datetime(dates), 'Gusts': gusts})
            
            # Plot
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(COLORS['bg'])
            ax.set_facecolor(COLORS['bg'])
            
            # Area chart for "Volatility" feel
            ax.fill_between(df['Date'], df['Gusts'], color=COLORS['primary'], alpha=0.3)
            ax.plot(df['Date'], df['Gusts'], color=COLORS['primary'], linewidth=2)
            
            # Highlight extreme events (> 50 km/h)
            extreme = df[df['Gusts'] > 50]
            ax.scatter(extreme['Date'], extreme['Gusts'], color=COLORS['secondary'], s=50, zorder=5, label='High Wind Event (>50km/h)')
            
            # Trend Line (Rolling Max 7D)
            df['Rolling'] = df['Gusts'].rolling(window=7).mean()
            ax.plot(df['Date'], df['Rolling'], color=COLORS['text'], linestyle='--', alpha=0.5, linewidth=1, label='7-Day Trend')
            
            # Styling
            ax.set_title("Real-Time Risk: Peak Wind Gusts (Tornado Alley Proxy)", color=COLORS['text'], fontsize=14, fontweight="bold")
            ax.set_ylabel("Wind Speed (km/h)", color=COLORS['text'])
            ax.tick_params(colors=COLORS['text'])
            ax.grid(color=COLORS['grid'], linestyle=':', linewidth=0.5)
            
            for spine in ax.spines.values():
                spine.set_visible(False)
                
            ax.legend(facecolor=COLORS['bg'], labelcolor=COLORS['text'], framealpha=0, loc='upper left')
            
            # Annotation for max gust
            max_val = df['Gusts'].max()
            max_date = df.loc[df['Gusts'].idxmax(), 'Date']
            ax.text(max_date, max_val + 2, f"{max_val} km/h", color=COLORS['secondary'], fontweight='bold', ha='center')
            
            save_path = os.path.join(self.output_dir, "storm_chart.png")
            plt.savefig(save_path, facecolor=COLORS['bg'], dpi=120)
            plt.close()
            print("      ✅ Saved storm_chart.png (Real Open-Meteo Data)")
            
        except Exception as e:
            print(f"      ❌ Open-Meteo Fetch Failed: {e}")

if __name__ == "__main__":
    analyst = VisualAnalyst()
    analyst.generate_all_assets()

import pandas as pd
import numpy as np
from shapely.geometry import LineString, MultiPoint
import matplotlib.pyplot as plt

class EnergyMarketAnalyzer:
    """
    A class to analyze and visualize energy market data, specifically focusing on sell and purchase orders.
    """

    def __init__(self, df):
        """
        Initialize with a pandas DataFrame containing market data.
        """
        self.df = df

    def get_orders(self, hour, order_type):
        """
        Retrieve orders for a specific hour and type (Sell or Purchase).
        """
        orders = self.df.loc[(self.df['Hour'] == hour) & (self.df['Sale/Purchase'] == order_type)]
        if orders.empty:
            return None
        return orders.sort_values(by='Price', ascending=(order_type == 'Sell'))

    def calculate_clearing(self, hour):
        """
        Calculate the system marginal volume (SMV) and system marginal price (SMP) for a given hour.
        """
        sell_orders = self.get_orders(hour, 'Sell')
        purchase_orders = self.get_orders(hour, 'Purchase')

        if not sell_orders or not purchase_orders:
            return None, None

        sell_line = LineString(np.column_stack((sell_orders['Volume'], sell_orders['Price'])))
        purchase_line = LineString(np.column_stack((purchase_orders['Volume'], purchase_orders['Price'])))
        intersection = sell_line.intersection(purchase_line)

        if isinstance(intersection, (LineString, MultiPoint)):
            smv = min(intersection.coords.xy[0])
            smp = min(intersection.coords.xy[1])
        elif intersection.geom_type == 'Point':
            smv, smp = round(intersection.x, 1), round(intersection.y, 2)
        else:
            return None, None

        return smv, smp

    def calculate_price_sensitivity(self, hour, delta):
        """
        Calculate the price sensitivity for a given hour and volume delta.
        """
        smv, smp = self.calculate_clearing(hour)
        if smv is None or smp is None:
            return np.nan

        sell_orders = self.get_orders(hour, 'Sell')
        if not sell_orders:
            return np.nan

        relevant_orders = sell_orders[sell_orders['Volume'] >= smv + delta] if delta >= 0 else sell_orders[sell_orders['Volume'] <= smv + delta]
        if relevant_orders.empty:
            return np.nan
        return relevant_orders.iloc[0]['Price'] - smp

    def generate_sensitivity_report(self, deltas):
        """
        Generate a report of price sensitivity for different deltas and hours.
        """
        hours = self.df["Hour"].unique()
        report = pd.DataFrame({'Hour': hours})

        for delta in deltas:
            report[f'Δ+{delta}'] = report['Hour'].apply(lambda h: self.calculate_price_sensitivity(h, delta))
            report[f'Δ-{delta}'] = report['Hour'].apply(lambda h: self.calculate_price_sensitivity(h, -delta))

        return report

    def plot_clearing(self, hour):
        """
        Plot the bid-ask depth chart for a given hour.
        """
        sell_orders = self.get_orders(hour, 'Sell')
        purchase_orders = self.get_orders(hour, 'Purchase')

        if not sell_orders or not purchase_orders:
            print("No data available for this hour.")
            return

        smv, smp = self.calculate_clearing(hour)
        if smv is None or smp is None:
            return
        plt.figure(figsize=(12, 6))
        plt.step(purchase_orders['Volume'], purchase_orders['Price'], where='pre', label='Bid', color='green',marker='o')
        plt.step(sell_orders['Volume'], sell_orders['Price'], where='pre', label='Ask', color='red',marker='o')
        plt.fill_between(purchase_orders['Volume'], 0,purchase_orders['Price'], color='green', alpha=0.3)
        plt.fill_between(sell_orders['Volume'], 0, sell_orders['Price'], color='red', alpha=0.3)
        plt.title('Bid-Ask Depth Chart')
        plt.xlabel('Cumulative Volume')
        plt.ylabel('Price')
        plt.xlim(smv-500,smv+1500)
        plt.ylim(smp-40,smp+40)
        plt.ylabel("€/MWh",color="white")
        plt.xlabel("MW",color="white")
        plt.legend()

        plt.grid(True)
        plt.tick_params(colors='white')
        plt.plot(smv,smp, 'bo',markersize=15)
        plt.vlines(smv, smp-100, smp, color='g', linestyle='--', alpha=0.4)
        plt.hlines(smp, 0, smv, color='g', linestyle='--', alpha=0.4)
        plt.text(smv, smp-90, str(round(smv)), ha='center', va='center', color='red')
        plt.text(200, smp, str(round(smp,2)), ha='center', va='center', color='red')
        plt.show()

# Example Usage:
# df = pd.read_csv('market_data.csv')
# analyzer = EnergyMarketAnalyzer(df)
# sensitivity_report = analyzer.generate_sensitivity_report([500, 1000, 2000])
# analyzer.plot_clearing('12:00')

# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE
# %%

# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE
# -*- coding: utf-8 -*-
import dataiku
import pandas as pd, numpy as np
from dataiku import pandasutils as pdu
from shapely.geometry import LineString, MultiPoint
import pytz
from datetime import datetime



# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE


# -------------------------------------------------------------------------------- NOTEBOOK-CELL: CODE
# %%
def price_sensitivity(df,delta,hour):#hour as string
    smv,smp=f_clearing(df,hour)
    sell_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Sell')].sort_values(by='Price', ascending=True)
    #print('PS_HOUR:',hour,'SMV','SMP:',smv,smp,'max_vol:',str(max(sell_orders['Volume'])),'delta:', str(delta),'XX:',sell_orders['Volume'] >= smv + delta)
    if (max(sell_orders['Volume'])<= smv + delta) or (min(sell_orders['Volume'])>= smv + delta):
       return np.nan
    else:
       return sell_orders.loc[sell_orders['Volume'] >= smv + delta].iloc[0]['Price'] - smp
       

# %%
# def price_sensitivity(df,delta,hour):
#     smv,smp=f_clearing(df,hour)
#     sell_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Sell')].sort_values(by='Price', ascending=True)
#     return sell_orders.loc[sell_orders['Volume'] <= smv + delta].iloc[-1]['Price'] - smp
def f_clearing(df, hour):
    # Filter the dataframe for the specified hour
    # Separate the Sell and Purchase orders
    sell_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Sell')].sort_values(by='Price', ascending=True)
    purchase_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Purchase')].sort_values(by='Price', ascending=False)
    

    sell_line = LineString(np.column_stack((sell_orders['Volume'], sell_orders['Price'])))
    purchase_line = LineString(np.column_stack((purchase_orders['Volume'], purchase_orders['Price'])))
    intersection = sell_line.intersection(purchase_line)
    if isinstance(intersection, LineString):
    # Handle LineString intersection
        smv=min(intersection.coords.xy[0])
        smp=min(intersection.coords.xy[1])
    if isinstance(intersection, MultiPoint):
        smv=min(intersection.coords.xy[0])
        smp=min(intersection.coords.xy[1])
    elif intersection.geom_type == 'Point':
    # Handle Point intersection
        smp = round(intersection.y,2)
        smv = round(intersection.x,1)
    return (smv,smp)

def sensitivity_df(df,deltas=[500,1000,2000]):
    hours=df["Hour"].unique()
    #deltas=[500,1000,2000]
    clearings = [f_clearing(df,h) for h in hours]
    day_sensitivity = pd.DataFrame({
        "hour" : hours,
        "smv" : [clearing[0] for clearing in clearings],
    })
    for delta in deltas[::-1]:
        day_sensitivity["-"+ str(delta)]=[price_sensitivity(df,-delta,hour)  for hour in hours]
    day_sensitivity["smp"]  = [clearing[1] for clearing in clearings]
    for delta in deltas:
        day_sensitivity["+"+ str(delta)]=[price_sensitivity(df,delta,hour)  for hour in hours]
    # %%
    off_peak=["H1","H2","H3","H3B","H4","H5","H6","H7","H8","H21","H22","H23","H24"]
    # %%
    day_sensitivity['hour']=day_sensitivity['hour'].apply(lambda x: "H"+ x)
    day_sensitivity=day_sensitivity.rename(columns={"hour": "product"})
    # %%
    base_row=pd.DataFrame(
        day_sensitivity.mean(numeric_only=True).round(2)).T
    base_row['product']='base'
    peak_row=pd.DataFrame(
        day_sensitivity.loc[~day_sensitivity["product"].isin(off_peak)].mean(numeric_only=True).round(2)).T    
    peak_row['product']='peak'

    off_peak_row=pd.DataFrame(
    day_sensitivity.loc[day_sensitivity["product"].isin(off_peak)].mean(numeric_only=True).round(2)).T
    off_peak_row['product']='off_peak'
    day_sensitivity=pd.concat([base_row,peak_row,off_peak_row,day_sensitivity])
    #rearrange columns
    day_sensitivity_df = day_sensitivity[['product'] + [col for col in day_sensitivity.columns if col != 'product']]
    return day_sensitivity_df.round(2)



def plot_clearing(df,hour):
    sell_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Sell')].sort_values(by='Price', ascending=True)
    purchase_orders = df.loc[(df['Hour'] == hour) & (df['Sale/Purchase'] == 'Purchase')].sort_values(by='Price', ascending=False)
    sell_line = LineString(np.column_stack((sell_orders['Volume'], sell_orders['Price'])))
    purchase_line = LineString(np.column_stack((purchase_orders['Volume'], purchase_orders['Price'])))

    smv,smp=f_clearing(df,h)
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


# %%
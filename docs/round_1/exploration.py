import pandas as pd
import matplotlib.pyplot as plt

prices = pd.read_csv("data/prices_round_1_day_-2.csv", sep=';')
trades = pd.read_csv("data/trades_round_1_day_-2.csv", sep=';')

ash = prices[prices['product'] == "ASH_COATED_OSMIUM"]
ash = ash[ash['mid_price'] > 0]

root = prices[prices['product'] == "INTARIAN_PEPPER_ROOT"]
root = root[root['mid_price'] > 0]

ash["rolling_mean_50"] = ash['mid_price'].rolling(50).mean()
ash["rolling_mean_200"] = ash['mid_price'].rolling(200).mean()

# Plot both
plt.figure()
plt.plot(ash['timestamp'], ash['mid_price'], linewidth = 0.7, alpha = 0.8, label="mid")
plt.plot(ash['timestamp'], ash["rolling_mean_50"], label = "mean50")
plt.plot(ash['timestamp'], ash["rolling_mean_200"], label = "mean200")
plt.legend()
plt.title("Ash Mid Price")

plt.figure()
plt.plot(root['timestamp'], root['mid_price'])
plt.title("Root Mid Price")

plt.show()
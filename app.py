from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# 📌 グラフ生成関数（メモリリーク対策、初期表示修正）
def generate_chart(ticker, period, interval, support_range, resistance_range, tick_size, threshold):
    # 株価データ取得
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval, auto_adjust=True)

    # 高値・安値・終値データを四捨五入
    df["High"] = (df["High"] / tick_size).round() * tick_size
    df["Low"] = (df["Low"] / tick_size).round() * tick_size
    df["Close"] = (df["Close"] / tick_size).round() * tick_size
    df["is_bullish"] = df["Close"] > df["Open"]
    df["is_bearish"] = df["Close"] < df["Open"]

    # 指定範囲の価格リスト
    support_levels = np.arange(support_range[0], support_range[1] + tick_size, tick_size)
    resistance_levels = np.arange(resistance_range[0], resistance_range[1] + tick_size, tick_size)

    # 反発回数をカウント
    support_counts = {level: (df["Low"] == level).sum() for level in support_levels}
    resistance_counts = {level: (df["High"] == level).sum() for level in resistance_levels}

    # データフレーム化
    support_df = pd.DataFrame(list(support_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)
    resistance_df = pd.DataFrame(list(resistance_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)

    # 最大値取得
    max_support_count = support_df["Bounce_Count"].max()
    max_resistance_count = resistance_df["Bounce_Count"].max()
    max_support_prices = support_df[support_df["Bounce_Count"] == max_support_count]["Price"].tolist()
    max_resistance_prices = resistance_df[resistance_df["Bounce_Count"] == max_resistance_count]["Price"].tolist()

    # 📌 **3つのグラフを生成（メモリ最適化）**
    img_list = []

    # **終値・高値・安値の推移**
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["Close"], label="Close Price", color="blue", linewidth=1.5)
    plt.plot(df.index, df["High"], label="High Price", color="red", linestyle="dotted", alpha=0.5)
    plt.plot(df.index, df["Low"], label="Low Price", color="green", linestyle="dotted", alpha=0.5)

    for level in resistance_levels:
        plt.axhline(y=level, color="red", linestyle="--", alpha=0.3)
    for level in support_levels:
        plt.axhline(y=level, color="green", linestyle="--", alpha=0.3)

    plt.xlabel("Date")
    plt.ylabel("Price (JPY)")
    plt.title("SUMCO (3436.T) Weekly Prices & Support/Resistance Levels")
    plt.legend(["Close Price", "High Price", "Low Price"])
    plt.grid()

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    img_list.append(base64.b64encode(img.getvalue()).decode())
    plt.close()  # メモリ解放

    # **支持線の反発回数グラフ**
    plt.figure(figsize=(10, 4))
    plt.bar(support_df["Price"], support_df["Bounce_Count"], width=tick_size, color="green", alpha=0.7)
    plt.xlabel("Price Level (JPY)")
    plt.ylabel("Bounce_Count")
    plt.title("Support Levels Bounce Count")
    plt.xticks(rotation=90)
    plt.yticks(np.arange(0, support_df["Bounce_Count"].max() + 2, 1))
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # **最大値リセット**
    plt.clf()  # グラフをクリア
    plt.text(support_df["Price"].min() + 0.5, max_support_count + .5, 
             f"Max Bounce Count: {max_support_count}\nMax Prices: " + ", ".join(map(str, max_support_prices)),
             fontsize=12, verticalalignment='top')

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    img_list.append(base64.b64encode(img.getvalue()).decode())
    plt.close()  # メモリ解放

    # **抵抗線の反発回数グラフ**
    plt.figure(figsize=(10, 4))
    plt.bar(resistance_df["Price"], resistance_df["Bounce_Count"], width=tick_size, color="red", alpha=0.7)
    plt.xlabel("Price Level (JPY)")
    plt.ylabel("Bounce_Count")
    plt.title("Resistance Levels Bounce Count")
    plt.xticks(rotation=90)
    plt.yticks(np.arange(0, resistance_df["Bounce_Count"].max() + 2, 1))
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # **最大値リセット**
    plt.clf()  # グラフをクリア
    plt.text(resistance_df["Price"].min() + 0.5, max_resistance_count + .5, 
             f"Max Bounce Count: {max_resistance_count}\nMax Prices: " + ", ".join(map(str, max_resistance_prices)),
             fontsize=12, verticalalignment='top')

    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    img_list.append(base64.b64encode(img.getvalue()).decode())
    plt.close()  # メモリ解放

    return img_list

# 📌 Webルート
@app.route("/", methods=["GET", "POST"])
def index():
    graph_urls = []  # **修正: 初期表示時は空リスト**
    if request.method == "POST":
        ticker = request.form["ticker"]
        period = request.form["period"]
        interval = request.form["interval"]
        support_range = (float(request.form["support_min"]), float(request.form["support_max"]))
        resistance_range = (float(request.form["resistance_min"]), float(request.form["resistance_max"]))
        tick_size = float(request.form["tick_size"])
        threshold = int(request.form["threshold"])
        graph_urls = generate_chart(ticker, period, interval, support_range, resistance_range, tick_size, threshold)

    return render_template("index.html", graph_urls=graph_urls)

if __name__ == "__main__":
    app.run(debug=True)

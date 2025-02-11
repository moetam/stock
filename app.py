from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# 📌 グラフ生成関数
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

    # 価格リスト
    support_levels = np.arange(support_range[0], support_range[1] + tick_size, tick_size)
    resistance_levels = np.arange(resistance_range[0], resistance_range[1] + tick_size, tick_size)

    # 反発回数をカウント
    support_counts = {level: (df["Low"] == level).sum() for level in support_levels}
    resistance_counts = {level: (df["High"] == level).sum() for level in resistance_levels}

    # データフレーム化
    support_df = pd.DataFrame(list(support_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)
    resistance_df = pd.DataFrame(list(resistance_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)

    # **上位5つの反発回数と、それに該当する価格を取得**
    top5_support_counts = support_df["Bounce_Count"].unique()[:5]
    top5_resistance_counts = resistance_df["Bounce_Count"].unique()[:5]

    top5_support_prices = [support_df[support_df["Bounce_Count"] == count]["Price"].tolist() for count in top5_support_counts]
    top5_resistance_prices = [resistance_df[resistance_df["Bounce_Count"] == count]["Price"].tolist() for count in top5_resistance_counts]

    # **グラフ作成**
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 📌 支持線のグラフ
    ax = axes[0]
    ax.bar(support_df["Price"], support_df["Bounce_Count"], width=tick_size, color="green", alpha=0.7)
    ax.set_xlabel("Price Level (JPY)")
    ax.set_ylabel("Bounce Count")
    ax.set_title("Support Levels Bounce Count")
    
    step = max(len(support_levels) // 10, 1)
    ax.set_xticks(support_levels[::step])
    ax.set_xticklabels(support_levels[::step], rotation=90)

    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.set_yticks(np.arange(0, max(support_df["Bounce_Count"].max(), 1) + 1, 1))

    # 📌 抵抗線のグラフ
    ax = axes[1]
    ax.bar(resistance_df["Price"], resistance_df["Bounce_Count"], width=tick_size, color="red", alpha=0.7)
    ax.set_xlabel("Price Level (JPY)")
    ax.set_ylabel("Bounce Count")
    ax.set_title("Resistance Levels Bounce Count")
    
    step = max(len(resistance_levels) // 10, 1)
    ax.set_xticks(resistance_levels[::step])
    ax.set_xticklabels(resistance_levels[::step], rotation=90)

    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.set_yticks(np.arange(0, max(resistance_df["Bounce_Count"].max(), 1) + 1, 1))

    # **画像をbase64エンコード**
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format="png")
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()

    # **ランキング用データ**
    support_ranking = [{"count": count, "prices": prices} for count, prices in zip(top5_support_counts, top5_support_prices)]
    resistance_ranking = [{"count": count, "prices": prices} for count, prices in zip(top5_resistance_counts, top5_resistance_prices)]

    return graph_url, support_ranking, resistance_ranking

# 📌 Webルート
@app.route("/", methods=["GET", "POST"])
def index():
    graph_url = None
    support_ranking = []
    resistance_ranking = []

    if request.method == "POST":
        ticker = request.form["ticker"]
        period = request.form["period"]
        interval = request.form["interval"]
        support_range = (float(request.form["support_min"]), float(request.form["support_max"]))
        resistance_range = (float(request.form["resistance_min"]), float(request.form["resistance_max"]))
        tick_size = float(request.form["tick_size"])
        threshold = int(request.form["threshold"])
        graph_url, support_ranking, resistance_ranking = generate_chart(ticker, period, interval, support_range, resistance_range, tick_size, threshold)

    return render_template("index.html", graph_url=graph_url, support_ranking=support_ranking, resistance_ranking=resistance_ranking)

if __name__ == "__main__":
    app.run(debug=True)

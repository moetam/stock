from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# 📌 グラフ生成関数（支持線・抑抗線を別々にする）
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

    # **グラフ生成関数（共通処理）**
    def create_graph(df, color, title, tick_size):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(df["Price"], df["Bounce_Count"], width=tick_size, color=color, alpha=0.7)
        ax.set_xlabel("Price Level (JPY)")
        ax.set_ylabel("Bounce Count")
        ax.set_title(title)

        # 📌 X軸の目目を min と max で 10 等分にする
        min_price, max_price = df["Price"].min(), df["Price"].max()
        xticks = np.linspace(min_price, max_price, num=10)  # 10等分のメモリを作成
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{x:.1f}" for x in xticks], rotation=90)

        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.set_yticks(np.arange(0, max(df["Bounce_Count"].max(), 1) + 1, 1))

        # 画像をbase64エンコード
        img = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img, format="png")
        img.seek(0)
        graph_url = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)

        return graph_url

    # 📌 個別のグラフを生成
    support_graph_url = create_graph(support_df, "green", "Support Levels Bounce Count", tick_size)
    resistance_graph_url = create_graph(resistance_df, "red", "Resistance Levels Bounce Count", tick_size)

    return support_graph_url, resistance_graph_url

# 📌 Webルート
@app.route("/", methods=["GET", "POST"])
def index():
    support_graph_url = None
    resistance_graph_url = None

    if request.method == "POST":
        ticker = request.form["ticker"]
        period = request.form["period"]
        interval = request.form["interval"]
        support_range = (float(request.form["support_min"]), float(request.form["support_max"]))
        resistance_range = (float(request.form["resistance_min"]), float(request.form["resistance_max"]))
        tick_size = float(request.form["tick_size"])
        threshold = int(request.form["threshold"])
        support_graph_url, resistance_graph_url = generate_chart(
            ticker, period, interval, support_range, resistance_range, tick_size, threshold
        )

    return render_template("index.html", support_graph_url=support_graph_url, resistance_graph_url=resistance_graph_url)

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

#入力値の検証
@app.route("/", methods=["GET", "POST"])
def check():
    support_graph_url = None
    resistance_graph_url = None
    support_ranking = []
    resistance_ranking = []
    error_message = None  # エラーメッセージの初期化

    if request.method == "POST":
        try:
            # 入力値を取得
            ticker = request.form["ticker"]
            period = request.form["period"]
            interval = request.form["interval"]
            support_min = float(request.form["support_min"])
            support_max = float(request.form["support_max"])
            resistance_min = float(request.form["resistance_min"])
            resistance_max = float(request.form["resistance_max"])
            tick_size = float(request.form["tick_size"])
            threshold = int(request.form["threshold"])

            # 銘柄コードの検証
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval, auto_adjust=True)
            if df.empty:
                error_message = "無効な銘柄コードが入力されました。正しい銘柄コードを入力してください。"

            # 入力値の検証
            elif support_min >= support_max:
                error_message = "支持線の最小値は最大値より小さくしてください。"
            elif resistance_min >= resistance_max:
                error_message = "抵抗線の最小値は最大値より小さくしてください。"
            elif tick_size <= 0:
                error_message = "刻み値は正の値を入力してください。"
            elif threshold < 0:
                error_message = "閾値は0以上の値を入力してください。"

            # エラーがない場合にグラフを生成
            if not error_message:
                support_range = (support_min, support_max)
                resistance_range = (resistance_min, resistance_max)
                support_graph_url, resistance_graph_url, support_ranking, resistance_ranking = generate_chart(
                    ticker, period, interval, support_range, resistance_range, tick_size, threshold
                )
        except ValueError:
            error_message = "正しい形式の数値を入力してください。"
        except Exception as e:
            error_message = f"エラーが発生しました: {e}"

    # テンプレートにデータを渡す
    return render_template(
        "index.html",
        support_graph_url=support_graph_url,
        resistance_graph_url=resistance_graph_url,
        support_ranking=support_ranking,
        resistance_ranking=resistance_ranking,
        error_message=error_message,
    )

# 📌 グラフ生成関数（支持線・抵抗線を別々にする）
def generate_chart(ticker, period, interval, support_range, resistance_range, tick_size, threshold):
    # 株価データ取得
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval, auto_adjust=True)

    # 高値・安値・終値データを四捨五入
    df["High"] = (df["High"] / tick_size).round() * tick_size
    df["Low"] = (df["Low"] / tick_size).round() * tick_size
    df["Close"] = (df["Close"] / tick_size).round() * tick_size
    df["is_bullish"] = (df["Close"] - threshold)> df["Open"]
    df["is_bearish"] = (df["Close"] + threshold) < df["Open"]

    #閾値内を除外
    df["bullish_High"] = np.where(df["is_bullish"] == True, df["High"], 0)
    df["bearish_Low"] = np.where(df["is_bearish"] == True, df["Low"], 0)

    # 価格リスト
    support_levels = np.arange(support_range[0], support_range[1] + tick_size, tick_size)
    resistance_levels = np.arange(resistance_range[0], resistance_range[1] + tick_size, tick_size)

    # 反発回数をカウント
    support_counts = {level: (df["bearish_Low"] == level).sum() for level in support_levels}
    resistance_counts = {level: (df["bullish_High"] == level).sum() for level in resistance_levels}

    #x軸
    step = 50
    support_xticks = support_levels[::step]
    resistance_xticks = resistance_levels[::step]

    # データフレーム化
    support_df = pd.DataFrame(list(support_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)
    resistance_df = pd.DataFrame(list(resistance_counts.items()), columns=["Price", "Bounce_Count"]).sort_values(by="Bounce_Count", ascending=False)

    # **ランキングデータ取得**
    top5_support_counts = support_df["Bounce_Count"].unique()[:5]
    top5_resistance_counts = resistance_df["Bounce_Count"].unique()[:5]

    support_ranking = [{"count": count, "prices": support_df[support_df["Bounce_Count"] == count]["Price"].tolist()} for count in top5_support_counts]
    resistance_ranking = [{"count": count, "prices": resistance_df[resistance_df["Bounce_Count"] == count]["Price"].tolist()} for count in top5_resistance_counts]

    # **グラフ生成関数（共通処理）**
    def create_graph(df, color, title, xticks):
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(df["Price"], df["Bounce_Count"], width=1, color=color, alpha=0.7)
        ax.set_xlabel("Price Level (JPY)")
        ax.set_ylabel("Bounce Count")
        ax.set_title(title)

        ax.set_xticks(xticks)
        ax.set_xticklabels(xticks, rotation=90)

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
    support_graph_url = create_graph(support_df, "green", "Support Levels Bounce Count", support_xticks)
    resistance_graph_url = create_graph(resistance_df, "red", "Resistance Levels Bounce Count", resistance_xticks)

    return support_graph_url, resistance_graph_url, support_ranking, resistance_ranking

# 📌 Webルート
@app.route("/", methods=["GET", "POST"])
def index():
    support_graph_url = None
    resistance_graph_url = None
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
        support_graph_url, resistance_graph_url, support_ranking, resistance_ranking = generate_chart(
            ticker, period, interval, support_range, resistance_range, tick_size, threshold
        )

    return render_template("index.html", support_graph_url=support_graph_url, resistance_graph_url=resistance_graph_url,
                           support_ranking=support_ranking, resistance_ranking=resistance_ranking)

if __name__ == "__main__":
    app.run(debug=True)

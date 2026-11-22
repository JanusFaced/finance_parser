import matplotlib.pyplot as plt
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError
import polars as pl
import numpy as np
from scipy.signal import periodogram
from scipy.signal import detrend
from datetime import datetime, timezone, timedelta
import dukascopy_python as duka
from dukascopy_python.instruments import (
    I_BTC_USD,
    I_ETH_USD,

    I_EUR_USD,
    I_GBP_USD,
    I_AUD_USD,
    I_NZD_USD,
    
    I_USD_JPY,
    I_USD_CHF,
    I_USD_CAD,

    I_XAU_USD,
    I_XAG_USD,
    I_COPPER_CMD_USD,
    
    I_USA500_IDX_USD,
    I_USATECH_IDX_USD,
    
    I_BRENT_CMD_USD,
    I_LIGHT_CMD_USD,
    I_GAS_CMD_USD,
    I_DIESEL_CMD_USD,

    I_SUGAR_CMD_USD,
    I_COCOA_CMD_USD,

    I_COFFEE_CMD_USX,
    I_COTTON_CMD_USX,
    I_SOYBEAN_CMD_USX,

    I_AAPL_US_USD,
    I_MSFT_US_USD,
    I_TSLA_US_USD,
    I_AMZN_US_USD,
    I_NVDA_US_USD,
    I_GOOGL_US_USD,
    I_JPM_US_USD,
    I_GE_US_USD,
    I_NFLX_US_USD,
    I_BABA_US_USD,
    I_TSM_US_USD,
    I_ORCL_US_USD,
    I_INTC_US_USD,
    I_AMD_US_USD,
    I_QCOM_US_USD,
    I_CSCO_US_USD,
    I_IBM_US_USD,
    I_BAC_US_USD,
    I_GS_US_USD,
    I_MS_US_USD,
    I_C_US_USD,
    I_V_US_USD,
    I_MA_US_USD,
    I_PEP_US_USD,
    I_KO_US_USD,
    I_PG_US_USD,

    I_USTBOND_TR_USD,
)
from pathlib import Path

output_dir = Path(__file__).parent / "output"

dataBase_password = os.getenv('DB_PASSWORD')
dataBase_user = os.getenv('DB_USER')
dataBase_name = os.getenv('DB_NAME')
dataBase_host = os.getenv('DB_HOST')
dataBase_port = os.getenv('DB_PORT')

DATABASE_URL = f"postgresql://{dataBase_user}:{dataBase_password}@{dataBase_host}:{dataBase_port}/{dataBase_name}"

def get_conn():
    return psycopg2.connect(
        host=dataBase_host,
        port=dataBase_port,
        user=dataBase_user,
        password=dataBase_password,
        dbname=dataBase_name,
    )

def table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (table,))
        return cur.fetchone()[0] is not None

def get_last_timestamp(conn, table: str) -> datetime | None:
    if not table_exists(conn, table):
        return None
    with conn.cursor() as cur:
        cur.execute(f"SELECT MAX(timestamp) FROM {table}")
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None

def parser() -> None:

    conn = get_conn()

    assets = {
        "BTC": I_BTC_USD,
        "ETH": I_ETH_USD,

        "EUR": I_EUR_USD,
        "GBP": I_GBP_USD,
        "AUD": I_AUD_USD,
        "NZD": I_NZD_USD,

        "JPY": I_USD_JPY,
        "CHF": I_USD_CHF,
        "CAD": I_USD_CAD,

        "XAU": I_XAU_USD,
        "XAG": I_XAG_USD,
        "COPPER": I_COPPER_CMD_USD,

        "USA500": I_USA500_IDX_USD,
        "USATECH": I_USATECH_IDX_USD,

        "BRENT": I_BRENT_CMD_USD,
        "LIGHT": I_LIGHT_CMD_USD,
        "GAS": I_GAS_CMD_USD,
        "DIESEL": I_DIESEL_CMD_USD,

        "SUGAR": I_SUGAR_CMD_USD,
        "COCOA": I_COCOA_CMD_USD,

        "COFFEE": I_COFFEE_CMD_USX,
        "COTTON": I_COTTON_CMD_USX,
        "SOYBEAN": I_SOYBEAN_CMD_USX,

        "AAPL": I_AAPL_US_USD,
        "MSFT": I_MSFT_US_USD,
        "TSLA": I_TSLA_US_USD,
        "AMZN": I_AMZN_US_USD,
        "NVDA": I_NVDA_US_USD,
        "GOOGL": I_GOOGL_US_USD,
        "JPM": I_JPM_US_USD,
        "GE": I_GE_US_USD,
        "NFLX": I_NFLX_US_USD,
        "BABA": I_BABA_US_USD,
        "TSM": I_TSM_US_USD,
        "ORCL": I_ORCL_US_USD,
        "INTC": I_INTC_US_USD,
        "AMD": I_AMD_US_USD,
        "QCOM": I_QCOM_US_USD,
        "CSCO": I_CSCO_US_USD,
        "IBM": I_IBM_US_USD,
        "BAC": I_BAC_US_USD,
        "GS": I_GS_US_USD,
        "MS": I_MS_US_USD,
        "C": I_C_US_USD,
        "V": I_V_US_USD,
        "MA": I_MA_US_USD,
        "PEP": I_PEP_US_USD,
        "KO": I_KO_US_USD,
        "PG": I_PG_US_USD,

        "USTBOND": I_USTBOND_TR_USD,
    }

    for symbol, instr in assets.items():

        tableName = (f"dukascopy_{symbol}_futures").lower()

        last_ts = get_last_timestamp(conn, tableName)

        delta_minute = timedelta(minutes=1)
        step_datetime = timedelta(days=7)
        current_datetime = datetime(2012, 1, 1, tzinfo=timezone.utc) if last_ts == None else last_ts

        while True:

            datetime_start = current_datetime
            datetime_end = datetime_start + step_datetime - delta_minute

            try:
                candles = duka.fetch_candles(
                    instrument=instr,
                    interval=1,
                    time_unit=duka.TimeUnit.MINUTE,
                    offer_side=duka.OfferSide.BID,
                    start=datetime_start,
                    end=datetime_end,
                )

            except:
                candles = []
                print("Error get data!")

            if len(candles) > 0:
                data = [
                    {
                        "timestamp": c.timestamp,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume,
                    }
                    for c in candles
                ]
                dataFrame = pl.from_dicts(data)

                dataFrame.write_database(
                    table_name=tableName,
                    connection=DATABASE_URL,
                    engine="adbc",
                    if_table_exists="append",
                )

            else:
                print("Lenth == 0!!!")

            current_datetime += step_datetime
            now_utc = datetime.now(timezone.utc)

            print(f" >>>>>> {current_datetime} <<<<<<")

            if delta_minute < (current_datetime - now_utc):
                print(" -> Max datetime! Stopping mine data!")
                break

def analyst() -> None:

    assets = {
        "BTC": I_BTC_USD,
        "ETH": I_ETH_USD,

        "EUR": I_EUR_USD,
        "GBP": I_GBP_USD,
        "AUD": I_AUD_USD,
        "NZD": I_NZD_USD,

        "JPY": I_USD_JPY,
        "CHF": I_USD_CHF,
        "CAD": I_USD_CAD,

        "XAU": I_XAU_USD,
        "XAG": I_XAG_USD,
        "COPPER": I_COPPER_CMD_USD,

        "USA500": I_USA500_IDX_USD,
        "USATECH": I_USATECH_IDX_USD,

        "BRENT": I_BRENT_CMD_USD,
        "LIGHT": I_LIGHT_CMD_USD,
        "GAS": I_GAS_CMD_USD,
        "DIESEL": I_DIESEL_CMD_USD,

        "SUGAR": I_SUGAR_CMD_USD,
        "COCOA": I_COCOA_CMD_USD,

        "COFFEE": I_COFFEE_CMD_USX,
        "COTTON": I_COTTON_CMD_USX,
        "SOYBEAN": I_SOYBEAN_CMD_USX,

        "AAPL": I_AAPL_US_USD,
        "MSFT": I_MSFT_US_USD,
        "TSLA": I_TSLA_US_USD,
        "AMZN": I_AMZN_US_USD,
        "NVDA": I_NVDA_US_USD,
        "GOOGL": I_GOOGL_US_USD,
        "JPM": I_JPM_US_USD,
        "GE": I_GE_US_USD,
        "NFLX": I_NFLX_US_USD,
        "BABA": I_BABA_US_USD,
        "TSM": I_TSM_US_USD,
        "ORCL": I_ORCL_US_USD,
        "INTC": I_INTC_US_USD,
        "AMD": I_AMD_US_USD,
        "QCOM": I_QCOM_US_USD,
        "CSCO": I_CSCO_US_USD,
        "IBM": I_IBM_US_USD,
        "BAC": I_BAC_US_USD,
        "GS": I_GS_US_USD,
        "MS": I_MS_US_USD,
        "C": I_C_US_USD,
        "V": I_V_US_USD,
        "MA": I_MA_US_USD,
        "PEP": I_PEP_US_USD,
        "KO": I_KO_US_USD,
        "PG": I_PG_US_USD,

        "USTBOND": I_USTBOND_TR_USD,
    }

    for symbol, _instr in assets.items():
        tableName = f"dukascopy_{symbol}_futures".lower()

        dataFrame = pl.read_database_uri(
            query=f"SELECT * FROM {tableName} ORDER BY timestamp",
            uri=DATABASE_URL,
            engine="adbc",
        )

        fileName: str = f"{output_dir}/{symbol.lower()}.png"
        plt.plot(dataFrame["timestamp"], dataFrame["close"], color="black")
        plt.savefig(fileName)
        plt.close()
        print(f"[{symbol}] saved {fileName}")

    print("End!")
    time.sleep(60)

def get_data(
        symbol: str,
        timeFrame: str,
        start: str,
        end: str
    ) -> pl.DataFrame:

    originalName = f"dukascopy_{symbol}_futures".lower()

    start = start.split("_")
    end = end.split("_")

    start = datetime(int(start[0]), int(start[1]), int(start[2]), 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(int(end[0]), int(end[1]), int(end[2]), 0, 0, 0, tzinfo=timezone.utc)

    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")

    dataFrame = pl.read_database_uri(
        query=f"""
            SELECT *
            FROM {originalName}
            WHERE timestamp >= '{start_str}'
              AND timestamp <  '{end_str}'
            ORDER BY timestamp
        """,
        uri=DATABASE_URL,
        engine="adbc",
    )

    resampled = (
        dataFrame
        .group_by_dynamic(
            index_column="timestamp",
            every=timeFrame,
            closed="left",
            label="left",
        )
        .agg([
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col("volume").sum(),
        ])
    )

    resampled = resampled.filter(pl.col("close").is_not_null())

    return resampled

def merge_closes(frames: dict[str, pl.DataFrame]) -> pl.DataFrame:
    dfs = [
        df.select(
            pl.col("timestamp"),
            pl.col("close").alias(sym.upper()),
        )
        for sym, df in frames.items()
    ]

    result = dfs[0]
    for other in dfs[1:]:
        result = result.join(other, on="timestamp", how="inner")

    return result.sort("timestamp")

def cooking_data(symbols, timeFrame, start, end):

    frames = {s: get_data(s, timeFrame, start, end) for s in symbols}

    dataFrame = merge_closes(frames)

    return dataFrame

def math_svd():

    symbols = [
        "BTC", "ETH",
        "EUR", "GBP", "AUD", "NZD",
        "XAU", "XAG", "COPPER",
        "USA500", "USATECH",
        "BRENT", "LIGHT", "GAS", "DIESEL",
        "SUGAR", "COCOA",
        "AAPL", "MSFT", "TSLA", "AMZN", "NVDA", "GOOGL", "JPM", "NFLX", "TSM", "INTC", "AMD", "QCOM",
        "USTBOND",
    ]

    dataFrame = cooking_data(symbols, "4h", "2019_01_01", "2026_11_19")

    timestamps = dataFrame["timestamp"].to_list()
    A = dataFrame.select(symbols).to_numpy().astype(np.float64)

    mean_vals = A.mean(axis=0)
    std_vals = A.std(axis=0)
    A_norm = (A - mean_vals) / std_vals

    U, S, Vt = np.linalg.svd(A_norm, full_matrices=False)

    n_factors = 5
    scores = U[:, :n_factors] * S[:n_factors]
    loadings = Vt[:n_factors, :]

    plt.figure(figsize=(14, 8))
    im = plt.imshow(loadings, cmap='coolwarm', aspect='auto', origin='lower')
    plt.colorbar(im, fraction=0.05)
    
    plt.title('Нагрузки активов на факторы (Стандартизированные)')
    plt.xlabel('Актив')
    plt.ylabel('Фактор (PC)')
    
    plt.xticks(range(len(symbols)), symbols, rotation=45, ha='right', fontsize=9)
    plt.yticks(range(n_factors), [f'Фактор {i+1}' for i in range(n_factors)])

    for x in range(loadings.shape[1]):
        for y in range(loadings.shape[0]):
            val = loadings[y, x]
            text_color = "white" if abs(val) > 0.6 else "black"
            plt.text(x, y, f'{val:.2f}', ha="center", va="center", color=text_color, fontweight='bold', fontsize=8)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/svd_heatmap.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Heatmap saved.")

    plt.figure(figsize=(14, 6))
    for i in range(n_factors):
        plt.plot(timestamps, scores[:, i], label=f'Фактор {i+1}', linewidth=1.5)
        
    plt.title('Динамика главных факторов во времени')
    plt.xlabel('Время')
    plt.ylabel('Значение фактора (Z-Score)')
    plt.legend(loc='upper left')
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/svd_time_series.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Time series saved!")

    explained_variance_ratio = (S**2) / np.sum(S**2) * 100
    cumulative_variance = np.cumsum(explained_variance_ratio)

    plt.figure(figsize=(12, 6))
    
    k_show = min(n_factors, len(S))
    x_ticks = range(1, k_show + 1)
    
    bars = plt.bar(x_ticks, explained_variance_ratio[:k_show], color='steelblue', alpha=0.7, label='Индивидуальный вклад')
    plt.plot(x_ticks, cumulative_variance[:k_show], 'ro-', linewidth=2, label='Накопленный итог')

    plt.title('Сила главных факторов (Explained Variance)')
    plt.xlabel('Номер компонента (PC)')
    plt.ylabel('Доля дисперсии (%)')
    plt.xticks(x_ticks)
    plt.grid(True, linestyle='--', alpha=0.3, axis='y')
    plt.legend()

    for i, v in enumerate(explained_variance_ratio[:k_show]):
        plt.text(i+1, v + 0.5, f'{v:.1f}%', ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(f"{output_dir}/svd_scree_plot.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Scree plot saved!")

    time.sleep(60)

def math_fourier():

    symbols = [
        "BTC", "ETH",
        "EUR", "GBP", "AUD", "NZD",
        "XAU", "XAG", "COPPER",
        "USA500", "USATECH",
        "BRENT", "LIGHT", "GAS", "DIESEL",
        "SUGAR", "COCOA",
        "AAPL", "MSFT", "TSLA", "AMZN", "NVDA", "GOOGL", "JPM", "NFLX", "TSM", "INTC", "AMD", "QCOM",
        "USTBOND",
    ]

    timeFrame = "4h"
    timeFrameNum = 4
    
    dayNum = 24
    minPeriodSize = 2
    maxPeriodSize = 2000

    start = "2019_01_01"
    end = "2026_11_19"

    average_window = 3

    dataFrame = cooking_data(symbols, timeFrame, start, end)

    for target_symbol in symbols:

        dataFrame = dataFrame.with_columns([
            pl.col(target_symbol).rolling_mean(window_size=average_window).alias('mean'),
        ])

        vector = dataFrame["mean"].to_numpy().astype(np.float64)
        vector = vector[np.isfinite(vector)]
        
        prices_detrended = detrend(vector, type='linear')

        fs = dayNum/timeFrameNum

        frequencies, power = periodogram(prices_detrended, fs=fs, scaling='spectrum')

        periods_days = (1/frequencies) / dayNum
        mask = (periods_days > minPeriodSize) & (periods_days < maxPeriodSize)

        plt.figure(figsize=(14, 7))

        plt.plot(periods_days[mask], power[mask], color='darkviolet', linewidth=1.5)
        plt.fill_between(periods_days[mask], power[mask], alpha=0.3, color='darkviolet')
        
        plt.title(f'Спектральный анализ: {target_symbol}\n(Поиск скрытых рыночных циклов)', fontsize=14)
        plt.xlabel('Длина цикла (в днях)', fontsize=12)
        plt.ylabel('Мощность влияния (Spectral Power)', fontsize=12)
        
        plt.axvline(x=30, color='red', linestyle='--', alpha=0.5, label='Размер месяца (30 дн.)')

        plt.xlim(left=10)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.legend(loc='upper right')
        
        if len(power[mask]) > 0:
            max_power_idx = np.argmax(power[mask])
            dominant_period = periods_days[mask][max_power_idx]
            plt.text(
                dominant_period, power[mask][max_power_idx], 
                f'Главный цикл: {dominant_period:.0f} свечей', 
                ha='center', va='bottom', fontsize=10, color='red', fontweight='bold'
            )

        plt.tight_layout()
        plt.savefig(f"{output_dir}/fourier_{target_symbol}.png", dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Анализ завершен. Главный найденный цикл для {target_symbol}: ~{dominant_period:.0f} дней.")

    print("End!")

    time.sleep(60)

def svd_fourier_hybrid():

    symbols = [
        "BTC", "ETH",
        "EUR", "GBP", "AUD", "NZD",
        "XAU", "XAG", "COPPER",
        "USA500", "USATECH",
        "BRENT", "LIGHT", "GAS", "DIESEL",
        "SUGAR", "COCOA",
        "AAPL", "MSFT", "TSLA", "AMZN", "NVDA", "GOOGL", "JPM", "NFLX", "TSM", "INTC", "AMD", "QCOM",
        "USTBOND",
    ]

    timeFrame = "4h"
    start = "2019_01_01"
    end = "2026_11_19"
    n_factors = 3
    
    minPeriodSize = 2
    maxPeriodSize = 365
    top_n = 3

    print("Загрузка и подготовка данных...")
    dataFrame = cooking_data(symbols, timeFrame, start, end)
    
    # Расчет коэффициента плотности (k_ratio) на основе всего датасета
    num_candles = len(dataFrame)
    real_start_datetime = dataFrame['timestamp'][0]
    real_end_datetime = dataFrame['timestamp'][-1]
    real_days = (real_end_datetime - real_start_datetime).total_seconds() / 86400.0
    k_ratio = num_candles / real_days if real_days > 0 else 1
    
    print(f"Коэффициент плотности данных (k): {k_ratio:.3f} свечей/день")

    # Очистка и нормализация
    A = dataFrame.select(symbols).drop_nulls().to_numpy().astype(np.float64)
    A_norm = (A - A.mean(axis=0)) / A.std(axis=0)
    
    # SVD разложение
    U, S, Vt = np.linalg.svd(A_norm, full_matrices=False)
    
    # Заголовок для сводной таблицы в консоли
    print(f"\n{'Актив':<10} | {'1-й цикл (дн.)':<15} | {'2-й цикл (дн.)':<15} | {'3-й цикл (дн.)':<15}")
    print("-" * 75)

    for index in range(len(symbols)):
        symbol = symbols[index]
        
        # 1. Восстановление теоретической цены через N факторов
        theoretical_signal = np.zeros(len(A))
        for i in range(n_factors):
            theoretical_signal += (U[:, i] * S[i]) * Vt[i, index]
        
        # 2. Расчет остатков (Residuals)
        residuals = A_norm[:, index] - theoretical_signal
        
        # 3. Фурье-анализ остатков
        res_detrended = detrend(residuals, type='linear')
        frequencies, power = periodogram(res_detrended, fs=1.0, scaling='spectrum')
        
        # Перевод в реальные дни с учетом k_ratio
        periods_days = (1.0 / frequencies[1:]) / k_ratio
        power_clean = power[1:]
        
        # Фильтрация диапазона
        mask = (periods_days > minPeriodSize) & (periods_days < maxPeriodSize)
        p_filtered = periods_days[mask]
        pow_filtered = power_clean[mask]
        
        # 4. Поиск ТОП-N уникальных пиков
        top_cycles = []
        if len(pow_filtered) > 0:
            # Сортируем индексы по убыванию мощности
            sorted_indices = np.argsort(pow_filtered)[::-1]
            
            for idx in sorted_indices:
                period = p_filtered[idx]
                power_val = pow_filtered[idx]
                
                # Проверка на уникальность (чтобы не взять два пика рядом)
                is_unique = True
                for existing_period, _ in top_cycles:
                    if abs(period - existing_period) < 5: # Допуск 5 дней
                        is_unique = False
                        break
                
                if is_unique:
                    top_cycles.append((round(period, 1), round(power_val, 4)))
                
                if len(top_cycles) >= top_n:
                    break
        
        # 5. Визуализация
        plt.figure(figsize=(12, 6))
        plt.vlines(p_filtered, 0, pow_filtered, color='crimson', linewidth=1.0, alpha=0.6)
        
        title_text = f'Спектр собственных циклов: {symbol}\n(После вычета {n_factors} глобальных факторов)'
        plt.title(title_text, fontsize=14)
        plt.xlabel('Период цикла (Реальные дни)')
        plt.ylabel('Мощность сигнала')
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.xlim(minPeriodSize, maxPeriodSize)
        
        # Отмечаем найденные топы на графике
        colors = ['black', 'blue', 'green']
        for i, (p, val) in enumerate(top_cycles):
            plt.vlines(p, 0, val, color=colors[i], linewidth=2.5, label=f'Топ-{i+1}: {p} дн.')
            
        if top_cycles:
            plt.legend(loc='upper right')
            
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{symbol}_svd_fourier_top{top_n}.png", dpi=150)
        plt.close()

        # Вывод в консоль
        c1 = f"{top_cycles[0][0]}" if len(top_cycles) > 0 else "-"
        c2 = f"{top_cycles[1][0]}" if len(top_cycles) > 1 else "-"
        c3 = f"{top_cycles[2][0]}" if len(top_cycles) > 2 else "-"
        print(f"{symbol:<10} | {c1:<15} | {c2:<15} | {c3:<15}")

    print("\nАнализ завершен! Графики сохранены.")
    time.sleep(60)

def main() -> None:

    mode = "svd_fourier_hybrid"

    if mode == "mine":
        parser()

    elif mode == "analyst":
        analyst()

    elif mode == "math_svd":
        math_svd()

    elif mode == "math_fourier":
        math_fourier()

    elif mode == "svd_fourier_hybrid":
        svd_fourier_hybrid()

    else:
        print("what?")

if __name__ == "__main__":
    main()
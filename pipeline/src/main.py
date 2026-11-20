import matplotlib.pyplot as plt
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError
import polars as pl
import numpy as np
from datetime import datetime, timezone, timedelta
import dukascopy_python as duka
from dukascopy_python.instruments import (
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

        "USTBOND": I_USTBOND_TR_USD,
    }

    for symbol, _instr in assets.items():
        tableName = f"dukascopy_{symbol}_futures".lower()

        dataFrame = pl.read_database_uri(
            query=f"SELECT * FROM {tableName} ORDER BY timestamp",
            uri=DATABASE_URL,
            engine="adbc",
        )

        print(f"[{symbol}] rows: {dataFrame.height}")

        start = datetime(2026, 2, 2, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 2, 3, 0, 0, 0, tzinfo=timezone.utc)

        dataFrame = dataFrame.filter(
            (pl.col("timestamp") >= start) & (pl.col("timestamp") < end)
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

def finance_math():

    symbols = ["EUR", "XAU", "USA500", "BRENT", "SUGAR", "AAPL", "USTBOND"]
    timeFrame = "4h"
    start, end = "2025_01_01", "2026_01_01"

    dataFrame = cooking_data(symbols, timeFrame, start, end)

    A = dataFrame.select(symbols).to_numpy().astype(np.float64)

    A_centered = A - A.mean(axis=0, keepdims=True)

    U, S, Vt = np.linalg.svd(A_centered, full_matrices=False)

    factor1 = U[:, 0] * S[0]
    factor2 = U[:, 1] * S[1]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    axes[0].plot(dataFrame["timestamp"], factor1)

    axes[1].plot(dataFrame["timestamp"], factor2)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/svd_factors.png")
    plt.close()

    print("End!")
    time.sleep(60)

def main() -> None:

    mode = "finance_math" # mine/analyst/finance_math

    if mode == "mine":
        parser()

    elif mode == "analyst":
        analyst()

    elif mode == "finance_math":
        finance_math()

    else:
        print("what?")

if __name__ == "__main__":
    main()
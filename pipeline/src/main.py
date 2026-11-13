import matplotlib.pyplot as plt
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError
import polars as pl
from datetime import datetime, timezone, timedelta
import dukascopy_python as duka
from dukascopy_python.instruments import (
    I_EUR_USD,
    I_GBP_USD,
    I_AUD_USD,
    I_NZD_USD,
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
    }

    for symbol, _instr in assets.items():
        tableName = f"dukascopy_{symbol}_futures".lower()

        dataFrame = pl.read_database_uri(
            query=f"SELECT * FROM {tableName} ORDER BY timestamp",
            uri=DATABASE_URL,
            engine="adbc",
        )

        print(f"[{symbol}] rows: {dataFrame.height}")

        dataFrame = dataFrame.tail(10000) 

        fileName: str = f"{output_dir}/{symbol.lower()}.png"
        plt.plot(dataFrame["timestamp"], dataFrame["close"], color="black")
        plt.savefig(fileName)
        plt.close()
        print(f"[{symbol}] saved {fileName}")

    print("End!")
    time.sleep(60)

def main() -> None:

    mode = "analyst" # mine/analyst

    if mode == "mine":
        parser()

    elif mode == "analyst":
        analyst()

    else:
        print("what?")

if __name__ == "__main__":
    main()
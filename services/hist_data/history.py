import pandas as pd
from pathlib import Path
import datetime as dt


data_path = Path('.') / 'data'


def get_trades(
    pair,
    data_path=data_path / 'trades'
):
    if pair[-4:] == '.csv':
        pair = pair[:-4]
    trades = (
        pd.read_csv(
            data_path / (pair + '.csv'),
            names=['timestamp', 'price', 'volume'],
        )
        .assign(
            datetime=(
                lambda x: (
                    x['timestamp']
                    .apply(lambda y: dt.datetime.fromtimestamp(y))
                )
            )
        )
    )
    return(trades)


def ohlc_from_trades(
    trades,
    freq='10s',
    datetime_col='datetime',
):
    return(
        trades
        .resample(freq, on=datetime_col)
        .agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': ['sum', 'count'],
        })
        .dropna()
        .reset_index()
        .assign(
            timestamp=lambda x: (
                x['datetime']
                .apply(lambda y: int(dt.datetime.timestamp(y)))
            )
        )
        .set_axis(
            [
                'datetime',
                'open',
                'high',
                'low',
                'close',
                'volume',
                'trade_count',
                'timestamp',
            ],
            axis=1,
        )
    )


def kraken_formatted_ohlc_from_trades(trades, freq='10s'):
    return(
        ohlc_from_trades(trades, freq=freq)[
            [
                'timestamp',
                'open',
                'high',
                'low',
                'close',
                'volume',
                'trade_count',
            ]
        ]
    )


def get_ohlc(pair, int_freq=60, compute_datetime=True):
    try:
        ohlc = (
            pd.read_csv(
                data_path / 'ohlc' / f'{pair}_{int_freq}sec.csv',
                names=[
                    'timestamp',
                    'open',
                    'high',
                    'low',
                    'close',
                    'volume',
                    'trade_count',
                ]
            )
        )
    except FileNotFoundError:
        ohlc = kraken_formatted_ohlc_from_trades(
            get_trades(pair),
            freq=f'{int_freq}s'
        )
        ohlc.to_csv(
            data_path / 'ohlc' / f'{pair}_{int_freq}sec.csv',
            index=False,
            header=False,
        )
    if compute_datetime:
        ohlc = ohlc.assign(datetime=lambda x: (
            x['timestamp']
            .apply(lambda y: dt.datetime.fromtimestamp(y))
            )
        )
    return(ohlc)

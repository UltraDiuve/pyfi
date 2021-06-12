import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
from typing import List


class Signal(object):
    # represents a buy or sell signal
    def __init__(
        self,
        base_asset=None,
        quote_asset=None,
        signal_type=None,
        datetime=None,
        volume=None,
        price=None,
    ) -> None:
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.signal_type = signal_type
        self.datetime = datetime
        self.volume = volume
        self.price = price


class VirtualPortfolio(object):
    # represents a portfolio during evaluation of a strategy
    def __init__(
        self,
        initial_volumes=None,
        datetimes=None,
        fee_rate=0.0026,
    ) -> None:
        self.assets = pd.DataFrame(
            initial_volumes,
            columns=list(initial_volumes.keys()),
            index=datetimes,
        ).astype(float)
        self.fees = pd.Series(
            0.,
            index=datetimes,
        )
        self.fee_rate = fee_rate

    def add_asset(
        self,
        asset_code,
        initial_volume=0.,
    ):
        if self.asset_exists(asset_code):
            raise RuntimeError(f"Asset {asset_code} already exists!")
        self.assets[asset_code] = float(initial_volume)

    def asset_exists(
        self,
        asset_code,
    ) -> bool:
        # return(asset_code in self.assets['asset_code'].unique())
        return(asset_code in self.assets.columns)

    def get_asset_current_volume(
        self,
        asset_code,
        datetime=None,
    ) -> float:
        if not datetime:
            datetime = self.assets.index.max()
        if not self.asset_exists(asset_code):
            self.add_asset(asset_code)
        return(self.assets.loc[datetime, asset_code])

    def update_asset_volume(
        self,
        asset_code,
        volume,
        increment=False,
        # allow_short_sell=False,
        datetime=None,
    ) -> None:
        if not datetime:
            datetime = self.assets.index.max()

        value_from = 0.
        if increment:
            value_from = self.get_asset_current_volume(
                asset_code,
                datetime=datetime,
            )
            new_volume = value_from + volume
        self.assets.loc[datetime:, asset_code] = new_volume

    def trade(
        self,
        asset_bought: str,
        asset_sold: str,
        price: float = None,
        volume_sold: float = None,
        allow_short_sale: bool = False,
        datetime=None,
        fees_ratio=0.0026,
    ):
        if not volume_sold:
            volume_sold = self.get_asset_current_volume(
                asset_sold,
                datetime=datetime,
            )

        if (
                volume_sold > self.get_asset_current_volume(
                    asset_sold,
                    datetime=datetime,
                ) and not allow_short_sale
        ):
            raise RuntimeError('Short selling whereas flag has not been set.')

        self.update_asset_volume(
            asset_sold,
            volume=-volume_sold,
            increment=True,
            datetime=datetime,
        )

        self.update_asset_volume(
            asset_bought,
            volume=volume_sold / price,
            increment=True,
            datetime=datetime,
        )

        # should be updated to take care of case fee is applied to trade
        # without asset being EUR
        if asset_bought == 'EUR':
            trade_value = volume_sold * price
        elif asset_sold == 'EUR':
            trade_value = volume_sold
        else:
            raise NotImplementedError(
                "fee computation to be implemented."
            )
        self.update_fees(
            trade_value=trade_value,
            overriden_fee_rate=None,
            datetime=datetime,
        )

    def update_fees(
        self,
        trade_value=0.,
        overriden_fee_rate=None,
        datetime=None,
    ):
        if not datetime:
            raise ValueError('datetime unspecified for fee computation')
        if overriden_fee_rate:
            fee_rate = overriden_fee_rate
        else:
            fee_rate = self.fee_rate
        self.fees.loc[datetime] += trade_value * fee_rate

    def pretty_trade(
        self,
        base_asset_code: str,
        quote_asset_code: str,
        market_price: bool = False,
        price: float = None,
        volume: float = None,
        allow_short_sale: bool = False,
        trade_type: str = 'buy',
        datetime=None,
        verbose=0,
    ) -> None:
        if market_price:
            raise NotImplementedError("Market price service to be integrated")

        if not market_price and not price:
            raise ValueError('Price not supplied for trade')

        if verbose >= 2:
            print(
                f'Trading: {trade_type} {base_asset_code} {quote_asset_code}'
                f' at price {price} for volume {volume}'
            )

        volume_sold = None

        if trade_type == 'buy':
            asset_sold = quote_asset_code
            asset_bought = base_asset_code
            price = price
            if volume:
                volume_sold = volume / price
        elif trade_type == 'sell':
            asset_sold = base_asset_code
            asset_bought = quote_asset_code
            price = 1 / price
            if volume:
                volume_sold = volume
        else:
            raise ValueError(f'Unexpected type:{type}')

        self.trade(
            asset_bought=asset_bought,
            asset_sold=asset_sold,
            price=price,
            volume_sold=volume_sold,
            allow_short_sale=allow_short_sale,
            datetime=datetime,
        )

    def __repr__(self):
        return(repr(self.assets))

    def historic_valorisation(
        self,
        prices_history=None,
        quote_asset='EUR',
    ):

        portfolio_values = pd.DataFrame(index=prices_history.index)

        # check if all current assets have prices in quote asset
        for asset in self.assets.columns:
            if (
                asset + quote_asset not in prices_history.columns and
                asset != quote_asset
            ):
                raise RuntimeError(f"asset {asset} missing in prices history")

        portfolio_values = pd.DataFrame(index=prices_history.index)
        portfolio_values[quote_asset] = self.assets[quote_asset]
        for asset in self.assets.columns:
            if asset == quote_asset:
                continue
            portfolio_values[asset] = (
                prices_history[asset + quote_asset] * self.assets[asset]
            )
        return(portfolio_values)

    def eval_performance(
        self,
        prices_history=None,
        quote_asset='EUR',
    ):
        values = self.historic_valorisation(
            prices_history=prices_history,
        ).sum(axis=1)
        return_ratio = values.iloc[-1] / values.iloc[0] - 1
        print(f"Return on period is: {return_ratio:.2%}")
        test_duration = self.assets.index.max() - self.assets.index.min()
        annualized_return = (
            (1 + return_ratio) ** (dt.timedelta(days=365) / test_duration) - 1
        )
        print(f"Annualized return on period is: {annualized_return:.2%}")
        total_fees = self.fees.sum()
        net_return_ratio = (values.iloc[-1] - total_fees) / values.iloc[0] - 1
        net_annualized_return = (
            (1 + net_return_ratio) ** (
                (dt.timedelta(days=365) / test_duration)
            ) - 1
        )
        print(f"Fees for trades are: {total_fees}")
        print(f"Net return on period is: {net_return_ratio:.2%}")
        print(
            f"Annualized net return on period is: {net_annualized_return:.2%}"
        )
        return({
            'return_ratio': return_ratio,
            'annualized_return_ratio': annualized_return,
            'total_fees': total_fees,
            'net_return_ratio': net_return_ratio,
            'net_annualized_return_ratio': net_annualized_return,
        })


class CrossAverageStrategy(object):
    # class which defines all attributes and methods common to all strategies

    def __init__(
        self,
        trading_pair=None,
        # profit_save_rate=0.,
        long_window=20,
        short_window=5,
    ) -> None:
        # self.profit_save_rate = profit_save_rate
        self.trading_pair = trading_pair
        self.long_window = long_window
        self.short_window = short_window

    def generate_signals(
        self,
        data,
        create_viz=False,
    ) -> List[Signal]:
        # here, data is a timeseries with asset price.
        price_series = data.loc[:, self.trading_pair]
        short_mv = price_series.rolling(self.short_window).mean(center=False)
        long_mv = price_series.rolling(self.long_window).mean(center=False)
        buys = (short_mv > long_mv) & ~(short_mv > long_mv).shift(1).iloc[1:]
        sells = ~(short_mv > long_mv) & (short_mv > long_mv).shift(1).iloc[1:]
        idxs = buys | sells
        signals = []
        for datetime in idxs.loc[idxs].index:
            if buys[datetime]:
                signal_type = 'buy'
            elif sells[datetime]:
                signal_type = 'sell'
            else:
                raise RuntimeError('Unexpected buy / sell type')
            signals.append(
                Signal(
                    base_asset='BTC',
                    quote_asset='EUR',
                    signal_type=signal_type,
                    datetime=datetime,
                    volume=None,
                )
            )

        if create_viz:
            fig, ax = plt.subplots(figsize=(20, 20))
            ax.plot(price_series)
            ax.plot(short_mv)
            ax.plot(long_mv)
            ax.scatter(
                buys[buys].index,
                price_series[buys[buys].index],
                marker="^",
                s=200,
                color='green',
            )
            ax.scatter(
                sells[sells].index,
                price_series[sells[sells].index],
                marker="v",
                s=200,
                color='red',
            )

        return(signals)

    def evaluate(
        self,
        price_history=None,
        initial_portfolio: VirtualPortfolio = None,
        create_viz=False,
        # initial_free_value=None,
    ) -> None:
        portfolio = initial_portfolio
        # price_history = price_history[self.trading_pair]
        # initial_portfolio_value = portfolio.eval_value(
        #     prices = pd.Series({
        #         'EUR': 1.0,
        #         'BTC': 100.,
        #     }),
        # )
        # free_value = initial_free_value
        signals = self.generate_signals(
            price_history,
            create_viz=create_viz,
        )

        if signals[0].signal_type == "sell":
            signals = signals[1:]
        for signal in signals:
            # print(price_history)
            price = price_history.loc[signal.datetime, self.trading_pair]
            # print(portfolio)
            portfolio.pretty_trade(
                signal.base_asset,
                signal.quote_asset,
                price=price,
                volume=None,
                allow_short_sale=False,
                trade_type=signal.signal_type,
                datetime=signal.datetime,
            )
        return(
            portfolio.eval_performance(
                prices_history=price_history,
            )
        )

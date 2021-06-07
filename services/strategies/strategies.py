from os import truncate
import pandas as pd
import datetime as dt


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
    ) -> None:
        self.assets = pd.DataFrame(
            initial_volumes,
            columns=list(initial_volumes.keys()),
            index=datetimes,
        ).astype(float)
    
    def add_asset(
        self,
        asset_code,
        initial_volume=0.,
    ):
        # if not self.asset_exists(asset_code):
        #     self.assets = pd.concat([
        #         self.assets,
        #         pd.DataFrame(
        #             [[asset_code, float(initial_volume)]],
        #             columns=['asset_code', 'volume']    
        #         )
        #     ]
        # )
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
        # if not allow_short_sell and new_volume < 0.:
        #     raise RuntimeError('Short selling whereas flag has not been set.')
        self.assets.loc[datetime:, asset_code] = new_volume

    def trade(
        self,
        asset_bought: str,
        asset_sold: str,
        price: float=None,
        volume_sold: float=None,
        allow_short_sale: bool=False,
        datetime=None,
    ):
        if not volume_sold:
            volume_sold = self.get_asset_current_volume(
                asset_sold,
                datetime=datetime,
            )

        if volume_sold > self.get_asset_current_volume(
                asset_sold,
                datetime=datetime,
            ) and not allow_short_sale:
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

    def pretty_trade(
        self,
        base_asset_code: str,
        quote_asset_code: str,
        market_price: bool=False,
        price: float=None,
        volume: float=None,
        allow_short_sale: bool=False,
        trade_type: str='buy',
        datetime=None,
    ) -> None:
        if market_price:
            raise NotImplemented("Market price service to be integrated")

        if not market_price and not price:
            raise ValueError('Price not supplied for trade')

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
            price = 1 /price
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

        # if trade_type == 'buy':
        #     sign = 1.
        # elif trade_type == 'sell':
        #     sign = -1.
        # else:
        #     raise ValueError(f'Unexpected type:{type}')

        # if not volume:
        #     if trade_type == 'buy':
        #         volume = self.get_asset_current_volume(quote_asset_code) / price
        #     if trade_type == 'sell':
        #         volume = self.get_asset_current_volume(base_asset_code)
        #     print(f'Computed volume is {volume}')



        # if not self.asset_exists(base_asset_code):
        #     self.add_asset(base_asset_code)
        # if not self.asset_exists(quote_asset_code):
        #     self.add_asset(quote_asset_code)
        # volume = volume * sign
        # total_price = price * volume
        # self.update_asset_volume(
        #     base_asset_code,
        #     volume,
        #     increment=True,
        #     allow_short_sell=allow_short_sell,
        # )
        # self.update_asset_volume(
        #     quote_asset_code,
        #     total_price * -1,
        #     increment=True,
        #     allow_short_sell=allow_short_sell,
        # )

    def __repr__(self):
        return(repr(self.assets))

    def eval_value(
        self,
        prices=None,
        quote_asset='EUR',
        date_of_value=None,
    ):
        eval = self.assets.set_index('asset_code').join(prices.rename('price'))
        eval['value'] = eval['volume'] * eval['price']
        return(eval['value']).sum()

    def eval_values(
        self,
        prices_history=None,
        quote_asset='EUR',    
    ):
        pass
        ### TO BE CONTINUED... Should have portfolio by date ?
        # check if all current assets have prices in quote asset
        # for asset in self.assets['asset'].unique():
        #     if (
        #         asset + quote_asset not in prices_history.columns and
        #         asset != quote_asset
        #     ):
        #         raise RuntimeError(f"asset {asset} missing in prices history")
            
        # portfolio_values = pd.DataFrame(index=prices_history.index)
        # for asset in self.assets['asset'].unique():
        #     if asset == quote_asset:


class CrossAverageStrategy(object):
    # class which defines all attributes and methods common to all strategies

    def __init__(
        self,
        trading_pair=None,
        profit_save_rate=0.,
    ) -> None:
        self.profit_save_rate = profit_save_rate
        self.trading_pair = trading_pair

    def generate_signals(
        self,
        data,
    ) -> list[Signal]:
        # this should be overriden in subclasses
        return(
            [
                Signal(
                    base_asset='BTC',
                    quote_asset='EUR',
                    signal_type='buy',
                    datetime=pd.to_datetime('2020-01-01'),
                    volume=None,
                ),
                Signal(
                    base_asset='BTC',
                    quote_asset='EUR',
                    signal_type='sell',
                    datetime=pd.to_datetime('2020-01-04'),
                    volume=None,
                ),
                Signal(
                    base_asset='BTC',
                    quote_asset='EUR',
                    signal_type='buy',
                    datetime=pd.to_datetime('2020-01-05'),
                    volume=None,
                ),
            ]
        )
        # raise(NotImplementedError)

    def evaluate(
        self,
        price_history=None,
        initial_portfolio: VirtualPortfolio=None,
        # initial_free_value=None,
    ) -> None:
        portfolio = initial_portfolio
        price_history = price_history[self.trading_pair]
        initial_portfolio_value = portfolio.eval_value(
            prices = pd.Series({
                'EUR': 1.0,
                'BTC': 100.,
            }),
        )
        # free_value = initial_free_value
        signals = self.generate_signals(price_history)
        if signals[0].signal_type == "sell":
            signals = signals[1:]
        for signal in signals:
            price = price_history[signal.datetime]
            # print(portfolio)
            portfolio.trade(
                signal.base_asset,
                signal.quote_asset,
                price=price_history[signal.datetime],
                volume=None,
                allow_short_sell=False,
                trade_type=signal.signal_type,
            )
        final_prices = pd.Series(
            {
                'EUR': 1.,
                'BTC': price_history.iloc[-1],
            }
        )
        final_value = portfolio.eval_value(final_prices)
        print(
            f"Evaluation of porfolio is: "
            f"{final_value}")
        return_ratio = (
            (final_value - initial_portfolio_value) / initial_portfolio_value
        )
        test_duration = price_history.index.max() - price_history.index.min()
        annualized_return = (1 + return_ratio) ** (dt.timedelta(days=365) / test_duration) - 1
        print(f"Percent return is: {return_ratio:.2%}")
        print(f"Annualized return is: {annualized_return:.2%}")
        return(portfolio)

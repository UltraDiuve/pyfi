import backtrader as bt
import backtrader.feeds as btfeeds

from pathlib import Path
import matplotlib

matplotlib.use('Agg')
data_path = Path('.') / 'data'


class TestStrategy(bt.Strategy):
    params = (
        ('shortperiod', 4),
        ('longperiod', 20),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0],
            period=self.params.shortperiod,
        )

        self.slow_sma = bt.indicators.SimpleMovingAverage(
                    self.datas[0],
                    period=self.params.longperiod,
                )

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(
        #     self.datas[0],
        #     period=25,
        # )
        # bt.indicators.WeightedMovingAverage(
        #     self.datas[0],
        #     period=25,
        #     subplot=True,
        # )
        # bt.indicators.StochasticSlow(self.datas[0])
        # bt.indicators.MACDHisto(self.datas[0])
        # rsi = bt.indicators.RSI(self.datas[0])
        # bt.indicators.SmoothedMovingAverage(
        #     rsi,
        #     period=10,
        # )
        # bt.indicators.ATR(
        #     self.datas[0],
        #     plot=False,
        # )

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        #  self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if (
                (self.fast_sma[0] > self.slow_sma[0]) and
                (self.fast_sma[-1] < self.slow_sma[-1])
            ):

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()

        else:

            if (
                (self.fast_sma[0] < self.slow_sma[0]) and
                (self.fast_sma[-1] > self.slow_sma[-1])
            ):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    # modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # datapath = os.path.join(modpath, '../../datas/orcl-1995-2014.txt')

    # Create a Data Feed
    data = btfeeds.GenericCSVData(
        dataname='./BTCEUR_2020_day.csv',
        nullvalue=0.0,
        dtformat=('%Y-%m-%d %H:%M:%S'),
        datetime=0,
        high=1,
        low=2,
        open=3,
        close=4,
        volume=5,
        openinterest=-1
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000.0)

    # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0026)

    cerebro.addsizer(bt.sizers.PercentSizer, percents=1.)

    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns', tann=252)
    cerebro.addanalyzer(
        bt.analyzers.SharpeRatio_A,
        _name='sharpe',
        timeframe=bt.TimeFrame.Days,
    )
    cerebro.addanalyzer(
        bt.analyzers.DrawDown,
        _name='drawdown',
    )

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    strats = cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    print('Sharpe Ratio:', strats[0].analyzers.sharpe.get_analysis())
    print('Returns: ', strats[0].analyzers.returns.get_analysis())
    print('Drawdown: ', strats[0].analyzers.drawdown.get_analysis())

    # Plot the result
    print('plotting')
    cerebro.plot()
    print('ended plotting')

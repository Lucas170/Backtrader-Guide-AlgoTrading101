import backtrader as bt

class PrintClose(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt)) #Print date and close

    def __init__(self):
        #Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        #Log closing price to 2 decimals
        self.log('Close: %.2f' % self.dataclose[0])

class MAcrossover(bt.Strategy): 
    # Moving average parameters
    params = (('pfast',7),('pslow',92),)

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt)) # Comment this line when running optimization

    def __init__(self):
        self.dataclose = self.datas[0].close
        # Order variable will contain ongoing order details/status
        self.order = None
        # Instantiate moving averages
        self.slow_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pslow)
        self.fast_sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.pfast)
        ''' Using the built-in crossover indicator
        self.crossover = bt.indicators.CrossOver(self.slow_sma, self.fast_sma)'''


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # An active Buy/Sell order has been submitted/accepted - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Reset orders
        self.order = None

    def next(self):
        ''' Logic for using the built-in crossover indicator
        
        if self.crossover > 0: # Fast ma crosses above slow ma
            pass # Signal for buy order
        elif self.crossover < 0: # Fast ma crosses below slow ma
            pass # Signal for sell order
        '''

        # Check for open orders
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # We are not in the market, look for a signal to OPEN trades
                
            #If the 20 SMA is above the 50 SMA
            if self.fast_sma[0] > self.slow_sma[0] and self.fast_sma[-1] < self.slow_sma[-1]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()
            #Otherwise if the 20 SMA is below the 50 SMA   
            elif self.fast_sma[0] < self.slow_sma[0] and self.fast_sma[-1] > self.slow_sma[-1]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
        else:
            # We are already in the market, look for a signal to CLOSE trades
            if len(self) >= (self.bar_executed + 5):
                self.log('CLOSE CREATE, %.2f' % self.dataclose[0])
                self.order = self.close()

class Screener_SMA(bt.Analyzer):
    params = (('period',20), ('devfactor',2),)

    def start(self):
        self.bbands = {data: bt.indicators.BollingerBands(data, period=self.params.period, devfactor=self.params.devfactor)
                     for data in self.datas}

    def stop(self):
        self.rets['over'] = list()
        self.rets['under'] = list()

        for data, band in self.bbands.items():
            node = data._name, data.close[0], round(band.lines.bot[0], 2)
            if data > band.lines.bot:
                self.rets['over'].append(node)
            else:
                self.rets['under'].append(node)

class AverageTrueRange(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt)) #Print date and close
        
    def __init__(self):
        #Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
    def next(self):
        range_total = 0
        for i in range(-13, 1):
            true_range = self.datahigh[i] - self.datalow[i]
            range_total += true_range
        ATR = range_total / 14

        self.log('Close: %.2f, ATR: %.4f' % (self.dataclose[0], ATR))

class BtcSentiment(bt.Strategy):
    params = (('period', 10), ('devfactor', 1),)

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.btc_price = self.datas[0].close
        self.google_sentiment = self.datas[1].close
        self.bbands = bt.indicators.BollingerBands(self.google_sentiment, period=self.params.period, devfactor=self.params.devfactor)

        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def next(self):
        # Check for open orders
        if self.order:
            return

        #Long signal 
        if self.google_sentiment > self.bbands.lines.top[0]:
            # Check if we are in the market
            if not self.position:
                self.log('Google Sentiment Value: %.2f' % self.google_sentiment[0])
                self.log('Top band: %.2f' % self.bbands.lines.top[0])
                # We are not in the market, we will open a trade
                self.log('***BUY CREATE, %.2f' % self.btc_price[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()       

        #Short signal
        elif self.google_sentiment < self.bbands.lines.bot[0]:
            # Check if we are in the market
            if not self.position:
                self.log('Google Sentiment Value: %.2f' % self.google_sentiment[0])
                self.log('Bottom band: %.2f' % self.bbands.lines.bot[0])
                # We are not in the market, we will open a trade
                self.log('***SELL CREATE, %.2f' % self.btc_price[0])
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()
        
        #Neutral signal - close any open trades     
        else:
            if self.position:
                # We are in the market, we will close the existing trade
                self.log('Google Sentiment Value: %.2f' % self.google_sentiment[0])
                self.log('Bottom band: %.2f' % self.bbands.lines.bot[0])
                self.log('Top band: %.2f' % self.bbands.lines.top[0])
                self.log('CLOSE CREATE, %.2f' % self.btc_price[0])
                self.order = self.close()
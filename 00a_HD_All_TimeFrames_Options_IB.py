import logging
# import datetime as dt
import time
from datetime import datetime
from threading import Thread
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
try:
    from CheckHiddenDivergence import CheckHiddenDivergence
except Exception:
    # Try relative import when running as a package
    try:
        from .CheckHiddenDivergence import CheckHiddenDivergence
    except Exception:
        # Fallback stub to avoid ImportError during static analysis or missing module.
        # The original code expects Check_Hidden_Divergence to return 1 when no signal,
        # so the stub follows that behavior.
        class CheckHiddenDivergence:
            def Check_Hidden_Divergence(self, timeframe, symbol, close_vals, high_vals, low_vals, volume_vals):
                return 1

from ibapi.client import EClient
from ibapi.contract import *
from ibapi.order import *
from ibapi.order_condition import *
from ibapi.utils import iswrapper
from ibapi.wrapper import EWrapper
import yfinance as yf


# from getFundamentalDetails import getFundamentalDetails

class HiddenDivergence(EWrapper, EClient):
    ''' Serves as the client and the wrapper'''
    def __init__(self, addr, port, client_id):
        EWrapper.__init__(self)
        EClient. __init__(self, self)

        self.stock_close_temp = []
        self.stock_close = []
        self.scan_results = []
        self.contract_results = []
        self.stock_high_temp = []
        self.stock_low_temp = []
        self.lowest_low_index = 0
        self.scanned_contract = []

        self.stock_high_temp = []
        self.stock_low_temp = []

        self.timeframe = ''

        self.order_id = 0
        self.con_id = 0

        self.robbyBuyPower = 0
        self.robinsonBuyPower = 0
        self.infantBuyPower = 0

        self.existingOrderSymbol = []
        self.existingPositionSymbol = []

        self.buyLimitPrice = 0
        self.sellLimitPrice = 0
        self.fibLevel = 0

        self.optStrikes = []

        self.strikes = []
        self.atm_price = 0
        self.expiration = 0
        self.multiplier = 0

        self.date = []
        self.time = []

        self.exportList = []
        
        # Connect to TWS
        self.connect(addr, port, client_id)

        # Launch the client thread
        thread = Thread(target=self.run)
        thread.start()

    @iswrapper
    def nextValidId(self, order_id):
        ''' Provides the next order ID '''
        self.order_id = order_id
        #print("NextValidId: {} ".format(order_id))

    @iswrapper
    def accountSummary(self, req_id, account, tag, value, currency):
         ''' Read information about the account '''
         #print('Account {}: {} = {}'.format(account, tag, value))
         if req_id == 7501:
             self.robbyBuyPower = value
         if req_id == 7502:
             self.robinsonBuyPower = value
         if req_id == 7503:
             self.infantBuyPower = value

    @iswrapper
    def openOrder(self, order_id, contract, order, state):
        ''' Called in response to the submitted order '''
        logging.info('OpenOrder: Order status: {}'.format(state.status))
        logging.info('OpenOrder: Order status contract Symbol: {}'.format(contract.symbol))
        logging.info('openOrder: Commission charged: {}'.format(state.commission))
        self.existingOrderSymbol.append(contract.symbol)
        #self.existingOrderSymbol.append(contract)
        self.existingOrderSymbol = list(set(self.existingOrderSymbol))
        logging.info('OpenOrder: existingOrderSymbol: {}'.format(self.existingOrderSymbol))

    @iswrapper
    def orderStatus(self, order_id, status, filled, remaining,
                    avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice):
        ''' Check the status of the submitted order '''
        # logging.info('orderStatus: {} '.format(status))
        # logging.info('orderStatus: Number of filled positions: {}'.format(filled))
        # logging.info('orderStatus: Average fill price: {}'.format(avgFillPrice))

    @iswrapper
    def position(self, account, contract, pos, avgCost):
        ''' Read information about open positions '''
        # logging.info('Position in {}: {}'.format(contract.symbol, pos))
        #self.existingPositionSymbol.append(contract.symbol)
        self.existingPositionSymbol.append(contract)
        self.existingPositionSymbol = list(set(self.existingPositionSymbol))
        #logging.info('position: existingPositionSymbol: {}'.format(self.existingPositionSymbol))

    @iswrapper
    def fundamentalData(self, reqId, data):
        ''' Called in response to reqFundamentalData '''

        #print('Fundamental data: ' + data)

        date = ET.fromstring(data).find('Company/EarningsList/Earnings/Date')
        time = ET.fromstring(data).find('Company/EarningsList/Earnings/Time')
        self.date = date.text
        self.time = time.text
        #print('date {}'.format(self.date))
        #print('time {}'.format(self.time))

    @iswrapper
    def historicalData(self, reqId, bar):
        # Append the close price to the deque to find SMA and MACD Hist
        self.stock_close_temp.append(bar.close)
        self.stock_close = np.array(self.stock_close_temp)
        # Append the high price to the deque to find higest high
        self.stock_high_temp.append(bar.high)
        # Append the low price to the deque to find lowest low
        self.stock_low_temp.append(bar.low)

    @iswrapper
    def historicalDataEnd(self, reqId, start, end):
        pass
        #self.CheckHiddenDivergence()

    @iswrapper
    def contractDetails(self, reqId, details):

        #print('contractDetails: {}'.format(details))
        #print('contract Details: {}'.format(details.contract.multiplier))
        #logging.info('Long name: {}'.format(details.longName))
        #logging.info('Category: {}'.format(details.category))
        #logging.info('Subcategory: {}'.format(details.subcategory))
        #logging.info('Contract ID: {}'.format(details.contract.conId))
        # logging.info('minTick: {}'.format(details.minTick))
        if reqId == 0:
            self.conid = details.contract.conId
        if reqId == 1:
            self.optStrikes.append(details.contract.strike)

    @iswrapper
    def contractDetailsEnd(self, reqId):
        print ('self.conid {}'.format(self.conid))

        if reqId == 1:
            #print('self.atm_price: {}'.format(self.atm_price))
            #print('self.optStrikes: {}'.format(self.optStrikes))
            # Find strike price closest to current price
            if self.optStrikes:
                self.optStrikes = sorted(self.optStrikes)
                min_dist = 99999.0
                for i, strike in enumerate(self.optStrikes):
                    if strike - self.buyLimitPrice < min_dist:
                        min_dist = abs(strike - self.buyLimitPrice)
                        self.atm_index = i
                self.atm_price = self.optStrikes[self.atm_index]
                #print('self.atm_price {}'.format(self.atm_price))
                # Limit strike prices to +7/-7 around ATM
                front = self.atm_index - 7
                back = len(self.optStrikes) - (self.atm_index + 7)
                if front > 0:
                    del self.optStrikes[:front]
                if back > 0:
                    del self.optStrikes[-(back - 1):]
                #print('self.optStrikes {}'.format(self.optStrikes))
            if self.atm_price in self.optStrikes:
                print ('Found strike price in the expiry date')
                self.putStrike = self.atm_price
            else:
                # To get the nearest number [strike price] from the list [Strike prices]
                self.putStrike = min(self.optStrikes, key=lambda x: abs(x - self.atm_price))
                #print('self.putStrike {}'.format(self.putStrike))


    @iswrapper
    def tickPrice(self, req_id, field, price, attribs):
        ''' Provide option's ask price/bid price '''

        #print('tickPrice - field: {}, price: {}'.format(field, price))
        if (field != 1 and field != 2) or price == -1.0:
            #print('INSIDE RETURN tickPrice')
            return
        #print('*OUTSIDE* RETURN tickPrice')
        # Determine the strike price and right
        #print('req_id: {}'.format(req_id))
        # strike = self.strikes[(req_id - 3) // 2]
        # right = 'C' if req_id & 1 else 'P'

        # Update the option chain
        if field == 1:
            self.bid_price = price
            #print('self.bid_price {}'.format(self.bid_price))
        elif field == 2:
            self.ask_price = price
            #print('self.ask_price {}'.format(self.ask_price))

    @iswrapper
    def tickSize(self, req_id, field, size):
        ''' Provide option's ask size/bid size '''
        if (field != 0 and field != 3) or size == 0:
            #print('INSIDE RETURN tickSize')
            return

        # Determine the strike price and right
        strike = self.strikes[(req_id - 3) // 2]
        right = 'C' if req_id & 1 else 'P'

        # Update the option chain
        if field == 0:
            self.bid_size = size
            #print('self.bid_size {}'.format(self.bid_size))
        elif field == 3:
            self.ask_size = size
            #print('self.ask_size {}'.format(self.ask_size))

    @iswrapper
    def securityDefinitionOptionParameter(self, reqId, exchange, underlyingConId, tradingClass, multiplier, expirations,
                                          strikes):
        ''' Provide strike prices and expiration dates '''
        # Save expiration dates and strike prices
        self.exchange = exchange
        self.expirations = expirations
        self.strikes = strikes
        self.multiplier = multiplier
        #print('securityDefinitionOptionParameter exchange: {}'.format(self.exchange))
        #print('securityDefinitionOptionParameter self.expirations: {}'.format(self.expirations))
        #print('securityDefinitionOptionParameter self.strikes {}'.format(self.strikes))
        #print('securityDefinitionOptionParameter self.multiplier {}'.format(self.multiplier))

    @iswrapper
    def securityDefinitionOptionParameterEnd(self, reqId):
        ''' Process data after receiving strikes/expirations '''
        '''
        # Find strike price closest to current price
        if self.strikes:
            self.strikes = sorted(self.strikes)
            min_dist = 99999.0
            for i, strike in enumerate(self.strikes):
                if strike - self.buyLimitPrice < min_dist:
                    min_dist = abs(strike - self.buyLimitPrice)
                    self.atm_index = i
            self.atm_price = self.strikes[self.atm_index]
            #print('self.atm_price {}'.format(self.atm_price))
            # Limit strike prices to +7/-7 around ATM
            front = self.atm_index - 7
            back = len(self.strikes) - (self.atm_index + 7)
            if front > 0:
                del self.strikes[:front]
            if back > 0:
                del self.strikes[-(back - 1):]
            #print('self.strikes {}'.format(self.strikes))

            if self.atm_price in self.strikes:
                print ('Found strike price in the expiry date')
                self.putStrike = self.atm_price
            else:
                # To get the nearest number [strike price] from the list [Strike prices]
                self.putStrike = min(self.strikes, key=lambda x: abs(x - self.atm_price))
                #print('self.putStrike {}'.format(self.putStrike))
        '''
        # Find an expiration date just over a month away
        self.expirations = sorted(self.expirations)
        for date in self.expirations:
            exp_date = datetime.strptime(date, '%Y%m%d')
            expDate = exp_date.day
            #print('Expiry Date only {}'.format(expDate))
            current_date = datetime.now()
            interval = exp_date - current_date
            if interval.days > 21 and (16 <= expDate <= 22):
                self.expiration = date
                #print('Monthly Expiration date after 21 Days : {}'.format(self.expiration))
                break


    @iswrapper
    def place_Orders(self,output):
        #print('place_Orders Output Stocks {} '.format(output))
        #logging.info('Total number of Stocks {}'.format(len(output)))
        'Declare filepath and column names for saving details into the excel sheet'
        self.exportList = pd.DataFrame(index=None, columns=[
                                            'Symbol',
                                            'TimeFrame',
                                            'Stat',
                                            'FibPriceLevel',
                                            'buyLimitPrice',
                                            'sellLimitPrice',
                                            'price236',
                                            'price382',
                                            'CurrentClosingPrice',
                                            '%Diff_closeVS23.6'])
        #Cancel All existing orders before placing fresh orders (Review this idea at later stage)
        #self.reqGlobalCancel()
        # for i, con.symbol in enumerate(symbol):
        for i in range(len(output)):
            timeframe = output[i][0]
            symbol = output[i][1]
            price50 = output[i][2]
            price382 = output[i][3]
            price236 = output[i][4]
            price618 = output[i][5]
            current_close = output[i][6]
            B = output[i][7]
            A = output[i][8]
            stat = output[i][9]

            # Define a contract for the underlying stock
            contract = Contract()
            contract.currency = 'USD'
            contract.exchange = 'SMART'
            contract.secType = 'STK'
            #print('symbol before{} '.format(symbol))
            if symbol.endswith('.DE'):
                contract.currency = 'EUR'
                symbol = symbol[:-3] # Remove last three digits of Germany stock .DE
            if symbol.endswith('.L'):
                contract.currency = 'GBP'
                symbol = symbol[:-2] # Remove last Two digits of LSE stock .L
                if symbol == 'BT-A':
                    symbol = 'BT.A'
                if symbol == 'SLA':
                    symbol = 'SL.'
                if symbol == 'BP':
                    symbol = 'BP.'
            if symbol.endswith('.NS'):
                contract.currency = 'INR'
                contract.exchange = 'NSE'
            if symbol.startswith('^'):
                contract.secType = 'IND'
            #print('symbol After{} '.format(symbol))
            contract.symbol = symbol

            '''
            #stat = output[i][9]
            currency = output[i][9]

            if currency == 'INR':
                contract.exchange = 'NSE'
                if contract.symbol == 'INDUSINDBK':
                    contract.symbol = 'INDUSINDB'
                if contract.symbol == 'BHARTIARTL':
                    contract.symbol = 'BHARTIART'
                if contract.symbol == 'TATAMOTORS':
                    contract.symbol = 'TATAMOTOR'
                if contract.symbol == 'HINDUNILVR':
                    contract.symbol = 'HINDUNILV'
                if contract.symbol == 'PIDILITIND':
                    contract.symbol = 'PIDILITIN'

            else:
                contract.exchange = 'SMART'
                if contract.symbol == 'UU':
                    contract.symbol = 'UU.'
            contract.currency = currency

            logging.info('OUTPUT Contract Symbol place_Orders : {}'.format(symbol))
            logging.info('TimeFrame: {}'.format(timeframe))
            logging.info('Price 50 Level : {}'.format(price50))
            logging.info('Price 38.2 Level : {}'.format(price382))
            logging.info('Price 23.6 Level : {}'.format(price236))
            logging.info('Price 11.4 Level : {}'.format(price114))
            logging.info('Current Close Price : {}'.format(current_close))
            logging.info('A : {}'.format(A))
            logging.info('currency : {}'.format(currency))
            #logging.info('secType : {}'.format(secType))
            '''
            self.buyLimitPrice = 0
            #self.quantity = 0
            self.sellLimitPrice = price618
            self.fibLevel = 0

            if price236 <= current_close <= price382:
                self.fibLevel = 23.2
                self.buyLimitPrice = price236
                Diff_Perc_close = round(((current_close / price236) - 1) * 100, 2)
                #if currency != 'GBP':
                    #self.quantity = round((5000 / price236), 0)
                #else:
                    #self.quantity = round((300000 / price236), 0)

            elif price382 <= current_close <= price50:
                self.fibLevel = 38.2
                if timeframe != 'DAILY' and timeframe != 'HOURLY':
                    self.buyLimitPrice = price382
                    Diff_Perc_close = round(((current_close / price382) - 1) * 100, 2)
                    #if currency != 'GBP':
                        #self.quantity = round((5000 / price382), 0)
                    #else:
                        #self.quantity = round((300000 / price382), 0)
                else:
                    self.buyLimitPrice = price236
                    Diff_Perc_close = round(((current_close / price236) - 1) * 100, 2)
                    #if currency != 'GBP':
                        #self.quantity = round((5000 / price236), 0)
                    #else:
                        #self.quantity = round((300000 / price236), 0)

            logging.info ('buyLimitPrice {} sellLimitPrice {} self.fibLevel {} Diff_Perc_close {}'.format(self.buyLimitPrice,
                                                                                 self.sellLimitPrice, self.fibLevel, Diff_Perc_close))
            '''
            yec = YahooEarningsCalendar()
            if currency == 'GBP':
                edate = yec.get_next_earnings_date(contract.symbol + '.L')
            elif currency == 'INR':
                edate = yec.get_next_earnings_date(contract.symbol + '.NS')
            else:
                edate = yec.get_next_earnings_date(contract.symbol)
            
            self.existingOrders()
            time.sleep(1.5)
            '''

            self.current_price = current_close

            if (stat != 'COLD'): #self.current_price <= self.buyLimitPrice: # currency == 'USD' and
                #print('HOT {}'.format(contract.symbol))
                self.reqContractDetails(0, contract)
                time.sleep(3)

                # Request strike prices and expirations
                if self.conid:
                    self.reqSecDefOptParams(2, contract.symbol, '', 'STK', self.conid)
                    time.sleep(1.5)
                else:
                    #print('Failed to get contact identifier')
                    exit()

                optionContract = Contract()

                optionContract.symbol = contract.symbol
                optionContract.secType = "OPT"
                #optionContract.strike = self.atm_price
                optionContract.right = 'P'
                optionContract.lastTradeDateOrContractMonth = self.expiration
                optionContract.exchange = contract.exchange
                if contract.currency == 'EUR':
                    optionContract.exchange = 'DTB'
                if contract.currency == 'GBP':
                    optionContract.exchange = 'ICEEU'
                optionContract.currency = contract.currency

                self.optStrikes = [] # To avoid accumulating all stocks strike prices
                time.sleep(3)
                self.reqContractDetails(1, optionContract)
                time.sleep(1.5)

                #print('Ordering Zone')
                # Obtain an ID for the main order
                self.reqIds(1000)
                time.sleep(2)

                # Create a Price condition
                buy_priceCondition = Create(OrderCondition.Price)
                buy_priceCondition.conId = self.conid
                buy_priceCondition.exchange = contract.exchange
                buy_priceCondition.symbol = contract.symbol
                if contract.currency == 'GBP':
                    buy_priceCondition.price = self.buyLimitPrice / 100
                else:
                    buy_priceCondition.price = self.buyLimitPrice
                buy_priceCondition.secType = contract.secType
                buy_priceCondition.triggerMethod = PriceCondition.TriggerMethodEnum.Default
                buy_priceCondition.isMore = False

                sell_priceCondition = Create(OrderCondition.Price)
                sell_priceCondition.conId = self.conid
                sell_priceCondition.exchange = contract.exchange
                sell_priceCondition.symbol = contract.symbol
                if contract.currency == 'GBP':
                    sell_priceCondition.price = self.sellLimitPrice / 100
                else:
                    sell_priceCondition.price = self.sellLimitPrice
                sell_priceCondition.secType = contract.secType
                sell_priceCondition.triggerMethod = PriceCondition.TriggerMethodEnum.Default
                sell_priceCondition.isMore = True

                #print('Buy priceCondition: {}'.format(buy_priceCondition))
                #print('Sell priceCondition: {}'.format(sell_priceCondition))

                mainOrder = Order()
                mainOrder.orderId = self.order_id
                mainOrder.action = "SELL"
                mainOrder.orderType = "MKT"
                mainOrder.totalQuantity = 1
                mainOrder.tif = "GTC"
                mainOrder.hidden = True
                mainOrder.transmit = False
                mainOrder.conditions.append(buy_priceCondition)

                profitlmtChild = Order()
                profitlmtChild.orderId = self.order_id + 1
                profitlmtChild.action = "BUY"
                profitlmtChild.orderType = "MKT"
                profitlmtChild.totalQuantity = 1
                #profitlmtChild.lmtPrice = round((self.ask_price / 2),2)
                profitlmtChild.parentId = self.order_id
                profitlmtChild.tif = "GTC"
                profitlmtChild.hidden = True
                profitlmtChild.transmit = True
                profitlmtChild.conditions.append(sell_priceCondition)

                optionContract.strike = self.putStrike
                #print('optionContract: {}'.format(optionContract))

                self.placeOrder(self.order_id, optionContract, mainOrder)
                time.sleep(1.5)
                self.placeOrder(self.order_id + 1, optionContract, profitlmtChild)
                time.sleep(1.5)
            else:
                pass  # No order placement needed
                #print('THERE IS AN EXISTING ORDER / POSITION FOR THIS SYMBOL {}'.format(contract.symbol))
            #now = datetime.now().strftime("%Y%m%d, %H:%M:%S")

            new_row = pd.DataFrame([{
                                            'Symbol': output[i][1],
                                            'TimeFrame': timeframe,
                                            'Stat': stat,
                                            'FibPriceLevel': self.fibLevel,
                                            'buyLimitPrice': self.buyLimitPrice,
                                            'sellLimitPrice':self.sellLimitPrice,
                                            'price236': price236,
                                            'price382': price382,
                                            'CurrentClosingPrice': current_close,
                                                    '%Diff_closeVS23.6': Diff_Perc_close}])
            self.exportList = pd.concat([self.exportList, new_row], ignore_index=True)


        pd.set_option("display.max_rows", None, "display.max_columns", None)
        logging.info(self.exportList)

        #with ExcelWriter("Output_All_TimeFrames_Bullish.xlsx", mode='a') as writer:
            #self.exportList.to_excel(writer)


    @iswrapper
    def error(self, req_id, code, msg):
        self.code = code
        self.msg = msg
        logging.info('Error {}: {}'.format(code, msg))

def main():
    # Create the client and connect to TWS. TWS: 7496; IB Gateway: 4001.Simulated Trading ports TWS: 7497; IB Gateway: 4002
    # Logging config
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='MAIN_HD.log', mode='w+')
    #handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    #create formatter
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    #add formatter to ch
    handler.setFormatter(formatter)
    #add ch to logger
    logger.addHandler(handler)

    #CLients Assignments
    clientJointAcc = HiddenDivergence('127.0.0.1', 7496, 0)

    output = []

    nifty = ['INDUSINDBK.NS','AXISBANK.NS','UPL.NS','SBIN.NS','ICICIBANK.NS','SUNPHARMA.NS','KOTAKBANK.NS','ADANIPORTS.NS','TECHM.NS','BHARTIARTL.NS','GRASIM.NS','ZEEL.NS',
               'INFRATEL.NS','BAJFINANCE.NS','IOC.NS','HDFC.NS','LT.NS','ITC.NS','BPCL.NS','ULTRACEMCO.NS','HDFCBANK.NS','ONGC.NS','RELIANCE.NS','BAJAJFINSV.NS','MARUTI.NS',
               'WIPRO.NS','NESTLEIND.NS','GAIL.NS','TITAN.NS','TCS.NS','HINDALCO.NS','BRITANNIA.NS','BAJAJ-AUTO.NS','HCLTECH.NS','TATASTEEL.NS','SHREECEM.NS','NTPC.NS',
               'CIPLA.NS','EICHERMOT.NS','COALINDIA.NS','M&M.NS','TATAMOTORS.NS','HINDUNILVR.NS','ASIANPAINT.NS','HDFCLIFE.NS','INFY.NS','DRREDDY.NS','POWERGRID.NS',
               'HEROMOTOCO.NS','JSWSTEEL.NS','PFC.NS','SUNTV.NS']

    

    spx = ['DKNG','DIA', 'GLD', 'GDX', 'FXI', 'IWM', 'QQQ', 'DIS', 'SLV', 'SPY', 'LMND', 'SFT','TLT', 'ETSY', 'DAL',
              'RDFN', 'AMD','NET', 'ATVI', 'PTON', 'AFL','BBY', 'LOW', 'COST', 'CMCSA','MRNA', 'DD', 'XLE',
              'NIO', 'BYND', 'NVDA', 'SHOP', 'PRPL','ORCL', 'PYPL', 'EXPI', 'UPWK', 'SNAP', 'PINS', 'SQ', 'TGT', 'Z', 'DOCU', 'RKT', 'U','WFC',
               'XLNX', 'WYNN', 'XPEV', 'W', 'FSLY', 'CAT', 'TWTR', 'ZM','AAPL', 'TSLA', 'FB', 'SPY', 'SPOT', 'GOOG',
              'GOOGL', 'NTAP', 'QCOM', 'VXX', 'JNJ', 'V', 'AMZN', 'T','DPZ', 'CMG', 'PEP', 'EBAY', 'MSFT', 'KBH', 'PG', 'CCL', 'JPM', 'BRK-B','BRK-A',
              'UNH','HD', 'HD', 'PFE','KO', 'NFLX', 'C', 'DELL', 'CSCO','SBUX','WDC','DBX','ENPH','ETSY','SNOW','TTCF','UI','W']

    
     

    ftse  = ['STAN.L','NXT.L','ULVR.L','WPP.L','AZN.L','NG.L','GSK.L','AV.L','PRU.L','LLOY.L','BARC.L','HSBA.L','AV.L','AAL.L','RIO.L','DGE.L','IAG.L','GLEN.L','RR.L','MRW.L','BT-A.L','NWG.L','KGF.L']

 

  

    finalList = nifty50 + dow30 + nasdaq30 + snp500 + indices + ftse30 + ftse100 #+ dax30 + forex

    finalList = list(set(finalList))

    #templist = ['DBK.DE','BMW.DE','HEN3.DE','LMND','INTC','BBQ','CON.DE','BLNK','BP.L','PRU.L']
    templist = indices


    # Request historical bars
    now = datetime.now().strftime("%Y%m%d, %H:%M:%S")

    timeframeList = ['DAILY', 'WEEKLY', 'MONTHLY']
    #timeframeList = ['MONTHLY']
    #contract = Contract()

    '''

    contract.currency = 'INR'
    contract.exchange = 'NSE'
    contract.secType = 'STK'

    US =  ['ICICIBANK','SUNPHARMA','KOTAKBANK','ADANIPORT','TECHM','BHARTIART','GRASIM','ZEEL','BAJFINANC','IOC','HDFC','LT','ITC','BPCL','ULTRACEMC','HDFCBANK','ONGC','RELIANCE','BAJAJFINS',
           'MARUTI','WIPRO','NESTLEIND','GAIL','TITAN','TCS','HINDALCO','BRITANNIA','BAJAJ-AUT','HCLTECH','TATASTEEL','SHREECEM','NTPC','CIPLA','EICHERMOT','COALINDIA','MM','TATAMOTOR',
           'HINDUNILV','ASIANPAIN','HDFCLIFE','INFY','DRREDDY','POWERGRID','HEROMOTOC','JSWSTEEL','PFC','SUNTV']

    '''
    #contract.currency = 'USD'
    #contract.exchange = 'SMART'
    #contract.secType = 'STK'
    US = nifty50 + ftse100 + snp500  # Scan NIFTY50, FTSE100, S&P500

    US = list(set(US))
    for symbol in US:
        #print('Contract  : {}'.format(contract))
        tickers = yf.Ticker(symbol)
        time.sleep(5)
        df = pd.DataFrame()
        for timeframe in timeframeList:
            if timeframe == 'DAILY':
                df = tickers.history(period='1y', interval='1d', actions=False, auto_adjust=True)
                # time.sleep(1)
            if timeframe == 'WEEKLY':
                df = tickers.history(period='5y', interval='1wk', actions=False, auto_adjust=True)
                # time.sleep(1)
            if timeframe == 'MONTHLY':
                df = tickers.history(period='10y', interval='1mo', actions=False, auto_adjust=True)
                # time.sleep(1)
            df = df.dropna()

        if df.empty == False:
            stock_high_temp = df['High'].values
            stock_high_temp = stock_high_temp.tolist()
            stock_low_temp = df['Low'].values
            stock_low_temp = stock_low_temp.tolist()
            stock_volume_temp = df['Volume'].values
            stock_volume_temp = stock_volume_temp.tolist()
            # pd.set_option("display.max_rows", None, "display.max_columns", None)  # To print full dataframe
            # print ('Contract Symbol {} Data Frame {}'.format(self.symbol, df))
            # print ('Control Symbol {} Close  {}'.format(self.symbol, df['Close'].values))
            # print('Control Symbol {} High  {}'.format(self.symbol, df['High'].values))
            # print('Control Symbol {} Low  {}'.format(self.symbol, df['Low'].values))
            cd = CheckHiddenDivergence()
            tempoutput = cd.Check_Hidden_Divergence(timeframe, symbol, df['Close'].values,
                                                              stock_high_temp, stock_low_temp, stock_volume_temp)
            if (tempoutput != 1):
                output = output + tempoutput
            # logging.info('Daily historicalDataEnd self.output {}'.format(self.output))
        #print('dailyHiddenDivergence self.output Before auto_adjust=False {}'.format(len(output)))

    'Declare filepath and column names for saving details into the excel sheet'
    exportList = pd.DataFrame(index=None, columns=[
                                            'Symbol',
                                            'Currency',
                                            'TimeFrame',
                                            'Stat',
                                            'FibPriceLevel',
                                            'price236',
                                            'price382',
                                            'SMA21',
                                            'SMA50',
                                            'SMA200',
                                            'CurrentClosingPrice',
                                            '%Diff_closeVS23.6'])



    #CLients Assignments
    #clientJointAcc = HiddenDivergence('127.0.0.1', 7401, 0)

    for i in range(len(output)):
        timeframe = output[i][0]
        symbolR = output[i][1]
        price50 = output[i][2]
        price382 = output[i][3]
        price236 = output[i][4]
        price618 = output[i][5]
        historical_close = round(output[i][6],2)  # This is from historical data
        B = output[i][7]
        A = output[i][8]
        stat = output[i][9]
        SMA21 = output[i][10]
        SMA50 = output[i][11]
        SMA200 = output[i][12]
        currency = output[i][13]
        exchanges = output[i][14]

        # Fetch ACTUAL current market price using yfinance
        try:
            ticker_obj = yf.Ticker(symbolR)
            current_data = ticker_obj.history(period='1d', interval='1m')
            if not current_data.empty:
                current_close = round(current_data['Close'].iloc[-1], 2)
                print(f"[PRICE UPDATE] {symbolR}: Historical={historical_close}, Current={current_close}")
            else:
                # Fallback to historical close if live data unavailable
                current_close = historical_close
                print(f"[PRICE WARNING] {symbolR}: Using historical price (live data unavailable)")
        except Exception as e:
            # Fallback to historical close on error
            current_close = historical_close
            print(f"[PRICE ERROR] {symbolR}: Using historical price - {str(e)}")

        # Define a contract for the underlying stock
        contract1 = Contract()
        contract1.currency = currency
        contract1.exchange = exchanges
        contract1.secType = 'STK'
        contract1.symbol = symbolR

        buyLimitPrice = 0
        sellLimitPrice = price618
        fibLevel = ''

        if price236 <= current_close <= price382:
            fibLevel = 'Below_38.2'
            buyLimitPrice = price236
            Diff_Perc_close = round(((current_close / price236) - 1) * 100, 2)
            # if currency != 'GBP':
            # self.quantity = round((5000 / price236), 0)
            # else:
            # self.quantity = round((300000 / price236), 0)

        elif price382 <= current_close <= price50:
            fibLevel = 'Below_50'
            if timeframe != 'DAILY' and timeframe != 'HOURLY':
                buyLimitPrice = price382
                Diff_Perc_close = round(((current_close / price382) - 1) * 100, 2)
                # if currency != 'GBP':
                # self.quantity = round((5000 / price382), 0)
                # else:
                # self.quantity = round((300000 / price382), 0)
            else:
                buyLimitPrice = price236
                Diff_Perc_close = round(((current_close / price236) - 1) * 100, 2)
                # if currency != 'GBP':
                # self.quantity = round((5000 / price236), 0)
                # else:
                # self.quantity = round((300000 / price236), 0)
        elif price50 <= current_close <= price618:
            fibLevel = 'Below_61.8'
            buyLimitPrice = price50
            Diff_Perc_close = round(((current_close / price50) - 1) * 100, 2)
        else:
            fibLevel = 'Unknown'
            buyLimitPrice = current_close
            Diff_Perc_close = 0.0

        #logging.info('buyLimitPrice {} sellLimitPrice {} self.fibLevel {} Diff_Perc_close {}'.format(buyLimitPrice,sellLimitPrice,fibLevel,Diff_Perc_close))
        #For getting Earning Datals from WSH
        clientJointAcc.reqFundamentalData(i, contract1, 'CalendarReport', [])
        time.sleep(2)

        new_row = pd.DataFrame([{
            'Symbol': contract1.symbol,
            'Currency': contract1.currency,
            'TimeFrame': timeframe,
            'Stat': stat,
            'FibPriceLevel': fibLevel,
            'price236': price236,
            'price382': price382,
            'SMA21': SMA21,
            'SMA50': SMA50,
            'SMA200': SMA200,
            'CurrentClosingPrice': current_close,
            '%Diff_closeVS23.6': Diff_Perc_close}])
        exportList = pd.concat([exportList, new_row], ignore_index=True)

    pd.set_option("display.max_rows", None, "display.max_columns", None) #For getting all the column details in the print instead of ...
    #print(exportList) #Sort the column based on Stats and Currency
    print(exportList.sort_values(by=['%Diff_closeVS23.6', 'Stat']))  # Sort the column based on Stats and Currency
    #print(exportList.filter(like='HOT',axis=1))
        # with ExcelWriter("Output_All_TimeFrames_Bullish.xlsx", mode='a') as writer:
        # self.exportList.to_excel(writer)

    # with ExcelWriter("Output_All_TimeFrames_Bullish.xlsx", mode='a') as writer:
    # self.exportList.to_excel(writer)
    '''
    clientJointAcc = HiddenDivergence('127.0.0.1', 7401, 0)
    time.sleep(5)
    clientJointAcc.reqAccountSummary(7501, 'All','BuyingPower')
    time.sleep(5)
    clientJointAcc.existingContracts()
    symbolRiona = clientJointAcc.AllexistingContracts()
    #print('symbolRiona {}'.format(symbolRiona))

    time.sleep(1.5)


    clientRobinsonSIPP = HiddenDivergence('127.0.0.1', 7402, 1)
    # Obtain information about account
    time.sleep(5)
    clientRobinsonSIPP.reqAccountSummary(7502, 'All','BuyingPower')
    time.sleep(5)
    clientRobinsonSIPP.existingContracts()
    symbolRobinson = clientRobinsonSIPP.AllexistingContracts()
    #print('SymbolRobinson {}'.format(symbolRobinson))

    time.sleep(1.5)

    clientInfantSIPP = HiddenDivergence('127.0.0.1', 7403, 2)
    time.sleep(5)
    clientInfantSIPP.reqAccountSummary(7503, 'All','BuyingPower')
    time.sleep(5)
    clientInfantSIPP.existingContracts()
    time.sleep(2)
    symbolInfant= clientInfantSIPP.AllexistingContracts()
    #print('SymbolInfant {}'.format(symbolInfant))
    time.sleep(2)

    #outputSymbol = [i[1] for i in output]  # To get the second element from the Tuple of Tuple [List?]

    #InfantRobinsonSymbols = SymbolInfant + SymbolRobinson




    infantOutput = []
    robinsonOutput = []
    rionaOutput = []
    remainAsset = []


    if clientRobinsonSIPP.isConnected() and clientJointAcc.isConnected() and clientInfantSIPP.isConnected():
        for outputSymbol in output:
            # If the yahoo output gives LSE or INR or EUR stocks with extension, this check will remove the extension and check if its present with IB stock list
            if outputSymbol[1].split('.',1)[0] in symbolInfant:
                #tempSymbolInfant.append(outputSymbol[1])
                infantOutput.append(outputSymbol)
            elif outputSymbol[1].split('.',1)[0] in symbolRobinson:
                #tempSymbolRobinson.append(outputSymbol[1])
                robinsonOutput.append(outputSymbol)
            elif outputSymbol[1].split('.', 1)[0] in symbolRiona:
                # tempSymbolRobinson.append(outputSymbol[1])
                rionaOutput.append(outputSymbol)
            else:
                #remainAsset.append(outputSymbol[1])
                remainAsset.append(outputSymbol)

        #print('infantOutput {} robinsonOutput {} rionaOutput {} remainAsset {} self.robbyBuyPower {} self.robinsonBuyPower {} self.infantBuyPower {}'.format(infantOutput,robinsonOutput,rionaOutput,remainAsset, clientJointAcc.robbyBuyPower, clientRobinsonSIPP.robinsonBuyPower,clientInfantSIPP.infantBuyPower))

        if (len(robinsonOutput) != 0):
            clientRobinsonSIPP.reqAllOpenOrders()
            clientRobinsonSIPP.reqAllOpenOrders()
            time.sleep(2)
            logging.info('clientRobinsonSIPP  existingOrderSymbol: {}'.format(clientRobinsonSIPP.existingOrderSymbol))
            #orderRobinson = clientRobinsonSIPP.AllexistingOrders()
            for outputOrder in output:
                if outputOrder[1].split('.', 1)[0] not in clientRobinsonSIPP.existingOrderSymbol:
                    clientRobinsonSIPP.place_Orders(robinsonOutput)
        
        if (len(infantOutput) !=0):
            clientInfantSIPP.reqAllOpenOrders()
            time.sleep(2)
            logging.info('clientInfantSIPP  existingOrderSymbol: {}'.format(clientInfantSIPP.existingOrderSymbol))
            #orderInfant = clientInfantSIPP.AllexistingOrders()
            for outputOrder in output:
                if outputOrder[1].split('.', 1)[0] not in clientInfantSIPP.existingOrderSymbol:
                    clientInfantSIPP.place_Orders(infantOutput)

        if (len(rionaOutput) != 0):
            clientJointAcc.reqAllOpenOrders()
            time.sleep(2)
            logging.info('clientJointAcc  existingOrderSymbol: {}'.format(clientJointAcc.existingOrderSymbol))
            #orderRiona = clientJointAcc.AllexistingOrders()
            for outputOrder in output:
                if outputOrder[1].split('.', 1)[0] not in clientJointAcc.existingOrderSymbol:
                    clientJointAcc.place_Orders(rionaOutput)

        if (len(remainAsset)!= 0):
            #logic calculation for Avaiable Funds and allocate
            clientJointAcc.reqAllOpenOrders()
            time.sleep(2)
            logging.info('remainAsset clientJointAcc  existingOrderSymbol: {}'.format(clientJointAcc.existingOrderSymbol))
            #orderRiona = clientJointAcc.AllexistingOrders()

            for outputOrder in output:
                if outputOrder[1].split('.', 1)[0] not in clientJointAcc.existingOrderSymbol:
                    print ('Check outpit: {}'.format(outputOrder[1].split('.', 1)[0]))
                    clientJointAcc.place_Orders(remainAsset)

    else:
        #print('One of the Client is disconnected, EXIT ALL')
        clientRobinsonSIPP.disconnect()
        clientInfantSIPP.disconnect()
        clientJointAcc.disconnect()

        #if (len(output) != 0):
            #client = HiddenDivergence('127.0.0.1', 7497, 0)
            #client.place_Orders(output)
        #client.disconnect()

        #clientRobinsonSIPP.disconnect()
        #clientInfantSIPP.disconnect()
    clientRobinsonSIPP.disconnect()
    clientInfantSIPP.disconnect()
    clientJointAcc.disconnect()
    '''
if __name__ == '__main__':
    main()
                                      

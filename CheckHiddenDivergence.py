
import pandas as pd



from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.utils import iswrapper
from threading import Thread
from ibapi.contract import *
from datetime import datetime
#import datetime as dt
import time
import sys

from ibapi.order import *
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue
from ibapi.scanner import ScanData
from ibapi.ticktype import *

from ibapi.order_condition import *
import numpy as np
from lxml import etree

#from yahoo_earnings_calendar import YahooEarningsCalendar
#from getFundamentalDetails import getFundamentalDetails

import logging



                                    
class CheckHiddenDivergence(EWrapper, EClient):
    ''' Serves as the client and the wrapper'''

    def __init__(self):
        EWrapper.__init__(self)
        EClient. __init__(self, self)

        #stock_close_temp = []
        stock_close = []
        #self.scan_results = []
        #self.contract_results = []
        stock_high_temp = []
        stock_low_temp = []
        #self.lowest_low_index = 0
        self.scan_symbol = []             
        symbol = ''
        timeframe = ''
        #self.avg_volume = 0
 
        self.count = 0
        self.output = []

        #self.dividend = 0
        #self.DivYield = 0
        #self.marketcap = 0
        #self.LastEarningDate = ''
        #self.order_id = 0
        #self.con_id = 0
        #self.exch = ''

        # Connect to TWS
        #self.connect(addr, port, client_id)

        # Launch the client thread
        #thread = Thread(target=self.run)
        #thread.start()
                  
    @iswrapper    
    def movingAverage(self, close, MV_PERIOD):
        #logging.info('CLOSE Moving Average{}' .format(close))
        #MV_PERIOD = 50
        temp = np.cumsum(close, dtype=float)
        temp[MV_PERIOD:] = temp[MV_PERIOD:] - temp[:-MV_PERIOD]
        return temp[MV_PERIOD - 1:] / MV_PERIOD
    
    @iswrapper    
    def highestHigh(self, high):
        max_value = max(high)
        max_index = high.index(max_value)
        return max_value, max_index
    
    @iswrapper    
    def lowestLow(self, low):
        min_value = min(low)
        min_index = low.index(min_value)
        return min_value, min_index

    @iswrapper
    def ExpMovingAverage(self, values, window):
        weighs = np.exp(np.linspace(-1., 0., window))
        weighs /= weighs.sum()
        a = np.convolve(values, weighs, mode='full')[:len(values)]
        a[:window] = a[window]
        return a

    @iswrapper
    def computeMACD(self, x, slow=26, fast=12):
        emaslow = self.ExpMovingAverage(x, slow)
        emafast = self.ExpMovingAverage(x, fast)
        return emaslow, emafast, emafast-emaslow

    @iswrapper
    def custom_macd(self, close_prices, n_fast=12, n_slow=26, n_signal=9):
        """Calculate MACD, MACD Signal and MACD Histogram without using TA-Lib.

        :param close_prices: List or array of closing prices
        :param n_fast: Number of periods for the fast EMA
        :param n_slow: Number of periods for the slow EMA
        :param n_signal: Number of periods for the signal line
        :return: Tuple of (macd, macdsignal, macdhist)
        """
        # Calculate the fast and slow EMAs
        ema_fast = pd.Series(close_prices).ewm(span=n_fast, adjust=False).mean()
        ema_slow = pd.Series(close_prices).ewm(span=n_slow, adjust=False).mean()

        # Calculate MACD
        macd = ema_fast - ema_slow

        # Calculate MACD Signal
        macdsignal = macd.ewm(span=n_signal, adjust=False).mean()

        # Calculate MACD Histogram
        macdhist_temp = macd - macdsignal

        return macd, macdsignal, macdhist_temp
        
        
    @iswrapper
    def Check_Hidden_Divergence(self,timeframe,symbol,stock_close,stock_high_temp,stock_low_temp,stock_volume):
        NoOfCandles = -100
        latest_close = stock_close[-1]
        #logging.info('latest_close  : {}'.format(latest_close))

        #logging.info('stock_close {}'.format(stock_close))
        #logging.info('stock_high_temp {}'.format(stock_high_temp))
        #logging.info('stock_low_temp {}'.format(stock_low_temp))
        sma50_temp = self.movingAverage(stock_close,50)
        sma200_temp = self.movingAverage(stock_close,200)

        sma50 = sma50_temp[NoOfCandles:]
        sma200 = sma200_temp[NoOfCandles:]
        
        #logging.info('Simple Moving average 50 : {}'.format(sma50))
        #logging.info('Simple Moving average 50 65 : {}'.format(sma50[-52:]))
        #logging.info('LEN Simple Moving average 50 65 : {}'.format(len(sma50[-52:])))
        #logging.info('LEN Simple Moving average 50 : {}'.format(len(sma50)))
        
        #logging.info('Simple Moving average 200: {}'.format(sma200))
        #logging.info('Simple Moving average 200 65: {}'.format(sma200[-52:]))
        #logging.info('LEN Simple Moving average 200 65 : {}'.format(len(sma200[-52:])))
        #logging.info('LEN Simple Moving average 200 : {}'.format(len(sma200)))

        '''               
        MACD Line: (12-day EMA - 26-day EMA)
        Signal Line: 9-day EMA of MACD Line
        MACD Histogram: MACD Line - Signal Line       
        '''
        macd, macdsignal, macdhist_temp = self.custom_macd(stock_close, 12, 26, 9)  # Custom MACD function replacing talib.MACD #nslow = 26 nfast = 12 nema = 9
        macdhist = macdhist_temp[NoOfCandles:]
        #print('macdhist_temp NoOfCandles  {} '.format(macdhist_temp))
        #print('macdhist NoOfCandles  {} '.format(macdhist))
        
        '''
        nslow = 26
        nfast = 12
        nema = 9
        emaslow, emafast, macd_np = self.computeMACD(stock_close)
        ema9 = self.ExpMovingAverage(macd_np, nema)
        #logging.info('ema9  {} '.format(ema9))
        macdhist_np = macd_np-ema9
        #logging.info('macdhist_np  {} '.format(macdhist_np[NoOfCandles:]))
        '''

        'Check if MACD histogram for the past three days are negetive'
        if (macdhist.iloc[-1] > 0 or macdhist.iloc[-2] > 0 or macdhist.iloc[-3] > 0):
            #logging.info('MACD Histogram for the past three days are not negetive : Exit BAD STOCK 1')
            return 1

        # PRIORITY 2: Volume confirmation - ensure buying interest
        if len(stock_volume) >= 20:
            volume_sma = sum(stock_volume[-20:]) / 20
            latest_volume = stock_volume[-1]
            if latest_volume < volume_sma * 0.8:
                #logging.info(f'Volume too low ({latest_volume:.0f} vs avg {volume_sma:.0f}): Exit BAD STOCK 1A')
                return 1

        'For finding Highest High B and its associated Index'
        self.stock_high = stock_high_temp[NoOfCandles:]
        B, IndexB = self.highestHigh(self.stock_high)
        #self.stock_high = np.array(stock_high_temp[NoOfCandles:])
        #logging.info('High Price  {} '.format(self.stock_high))
        #B = np.amax(self.stock_high)

        #IndexB = np.where(self.stock_high == np.amax(self.stock_high))
        #print('INDEXB {}'.format(IndexB))
        #IndexB = int(IndexB[0])
        #logging.info('Highest High : {}'.format(B))
        #logging.info('IndexB: {}'.format(IndexB))

        # PRIORITY 3: Pattern age limit - ensure pattern is fresh
        pattern_age = len(macdhist) - IndexB
        if pattern_age > 30:
            #logging.info(f'Pattern too old ({pattern_age} bars from high): Exit BAD STOCK 1B')
            return 1

        self.stock_low = stock_low_temp[NoOfCandles:]
        #logging.info('Low Price : {}'.format(self.stock_low))
        latest_low = self.stock_low[-1]  # Latest Current Low
        #logging.info('Current Low {}'.format(latest_low))
        

        #50 day Moving average should be always greater than 200 day moving average selected range
        # PRIORITY 1: SMA Trend Filter ENABLED - Only trade stocks in uptrends
        if(len(sma50) == len(sma200)):
            for i in range(0, len(sma50)):
                if(sma50[i] > sma200[i]):
                # logic
                    #logging.info ("GOOD STOCK")
                    continue
                else:
                # logic
                    #logging.info ("SMA50 is not greater than SMA200 : Exit BAD STOCK 2")
                    return 1  # Changed from break to return 1

        if macdhist.iloc[IndexB] < 0:  # Covered in final check, remember to remove at later stage
            #logging.info ('MACD Histogram for Higher B Index position is not positive : Exit BAD STOCK 3')
            return 1

        low1 = 0
        low2 = 0
        l = IndexB
        #logging.info ('MACD of Highest High {}'.format(macdhist.iloc[l]))
        while macdhist.iloc[l] > 0:
            l = l-1
            if(macdhist.iloc[l] < 0):
                low1 = l
                break
        #logging.info ('Inbetween LOW1 {} '.format(low1))
        m = low1
        while macdhist.iloc[m] < 0:
            m = m-1
            if macdhist.iloc[m] > 0:
                low2 = m
                break
            
        #logging.info ('LOW 1 {} LOW 2  {}'.format(low1,low2))
        
        templow = self.stock_low[low2+1:low1+1]
        if len(templow) == 0:
            #logging.info ('There are no lows within specified range : Exit BAD STOCK 4')
            return 1        
        #logging.info ('TEMP LOW {}'.format(templow))
        

        A = np.amin(templow)
        IndexA = self.stock_low.index(A)
        #IndexA = np.where(templow == np.amin(templow))
        #print('INDEXA {}'.format(IndexA))
        #IndexA = int(IndexA[0])

        #logging.info('First A : {}'.format(A))
        #logging.info('IndexA: {}'.format(IndexA))
        #logging.info('macdhist[low1] : {} macdhist[low2] {}'.format(macdhist[low1],macdhist[low2]))        
        #logging.info('Index A Lowest Lows MACD {}'.format(macdhist[IndexA]));

        # Validate IndexA
        if IndexA < 0 or IndexA >= len(macdhist):
            #logging.info('IndexA out of range: Exit BAD STOCK 12')
            return 1

        '''
        For finding Second low HD
        '''
        if (A > latest_low):
            #logging.info ('Find Second Low')
            i = 0
            low3 = 0
            low4 = 0
            tempsecondLow1 = low2
            while i < tempsecondLow1:
                #logging.info('tempsecondLow1',tempsecondLow1)
                #logging.info('self.stock_low[tempsecondLow1]',self.stock_low[tempsecondLow1])

                if(macdhist.iloc[tempsecondLow1] < 0 and self.stock_low[tempsecondLow1] < latest_low):
                    low3 = tempsecondLow1
                    break
                tempsecondLow1 = tempsecondLow1-1

            tempsecondLow2 = low3
            while macdhist.iloc[tempsecondLow2] < 0:
                tempsecondLow2 = tempsecondLow2-1
                if macdhist.iloc[tempsecondLow2] > 0:
                    low4 = tempsecondLow2
                    break
                
            tempsecondlow = self.stock_low[low4+1:low3+1]
            if len(tempsecondlow) == 0:
                #logging.info ('Second Low : There are no second lows within specified range : Exit BAD STOCK 5')
                return 1   
            
            SecondA = np.amin(tempsecondlow)
            SecondIndexA = self.stock_low.index(SecondA)
            #logging.info('Second A : {}'.format(SecondA))
            #logging.info('Second IndexA: {}'.format(SecondIndexA))

            # Validate SecondIndexA
            if SecondIndexA < 0 or SecondIndexA >= len(macdhist):
                #logging.info('SecondIndexA out of range: Exit BAD STOCK 13')
                return 1

            if (macdhist.iloc[SecondIndexA] > 0 or
                SecondIndexA > IndexB or
                macdhist.iloc[-1] > (0.8 * macdhist.iloc[SecondIndexA]) or
                latest_close < SecondA or
                latest_close > B):
                #logging.info ('Second Low : MACD Histogram for Lower B index position is not Negative.Lower A index position is not lower than Higher B index Position,MACD Histogram Current close should be atleast 80% of MACD Hist of Lower A index positon : Exit BAD STOCK 6')
                return 1

            prince618 = round((((38.2*A)+(61.8*B))/100),2)            
            price50 = round(((SecondA+B)/2),2)
            #logging.info('price50  : {}'.format(price50))
            price382 = round((((61.8*SecondA)+(38.2*B))/100),2)
            #logging.info('price61.8  : {}'.format(price382))
            price236 = round((((76.4*SecondA)+(23.6*B))/100),2)
            #logging.info('price76.4  : {}'.format(price236))
            price114 = round((((88.6*SecondA)+(11.4*B))/100),2)
            #logging.info('price88.6  : {}'.format(price114))   

            
            if (latest_close > price50 or
                latest_low < price114):
                #logging.info ('Second Low : Stock not within 50 to 11.4 range : Exit BAD STOCK 7')
                return 1          
        
            stock_low_temp1 = self.stock_low[IndexB:]
            #logger.info('INFO stock_low_temp1',stock_low_temp1)
            LowestFromBtoRecent, LowestFromBtoRecentIndex = self.lowestLow(stock_low_temp1)
            #logger.info('INFO LowestFromBtoRecent',LowestFromBtoRecent)
            #logger.info('INFO LowestFromBtoRecentIndex',LowestFromBtoRecentIndex)


            if (LowestFromBtoRecent < price114):
                #logging.info ('Second Low LowestFromBtoRecent: BAD STOCK 9 {}'.format(LowestFromBtoRecent))
                return 1
            '''
            #Screen nearning stocks
            if (latest_close > (1.05*price382) or
                latest_close > (1.05*price236) or
                latest_close > (1.05*price114)):
                #logging.info ('Second Low :  Stock not nearing purchasing AREA : Exit BAD STOCK 8')
                return 1
            '''                  
            logging.info ('Second Low : GOOD STOCK ZONE')
            # Get currency and exchange from symbol
            currency = "USD"
            exchange = "SMART"
            if symbol.endswith(".NS"):
                currency = "INR"
                exchange = "NSE"
            elif symbol.endswith(".L"):
                currency = "GBP"
                exchange = "LSE"
            elif symbol.endswith(".DE"):
                currency = "EUR"
                exchange = "XETRA"
            elif symbol.startswith("^"):
                exchange = "INDEX"
            
            # Calculate SMAs
            sma21_temp = self.movingAverage(stock_close, 21) if len(stock_close) > 21 else [0]
            sma50_temp = self.movingAverage(stock_close, 50) if len(stock_close) > 50 else [0]
            sma200_temp = self.movingAverage(stock_close, 200) if len(stock_close) > 200 else [0]
            sma21 = round(sma21_temp[-1], 2) if len(sma21_temp) > 0 else 0
            sma50 = round(sma50_temp[-1], 2) if len(sma50_temp) > 0 else 0
            sma200 = round(sma200_temp[-1], 2) if len(sma200_temp) > 0 else 0
            
            tempoutput = [timeframe,symbol,prince618,price50,price382,price236,price114,latest_close,B,SecondA,"HOT",sma21,sma50,sma200,currency,exchange]
            #logging.info('self.tempoutput : {}'.format(tempoutput))
            self.output.append([0] * len(tempoutput))  #Create memory for 2 dimentional list before assinging
            for i in range(len(tempoutput)):            
                #logging.info('self.tempoutput[i]',tempoutput[i])            
                self.output[self.count][i] = tempoutput[i]            
            #logging.info('self.output',self.output)
            #self.output[self.count] = (timeframe,symbol,prince382,price50,price618,price764,price886,latest_close,B,A)
            self.count = self.count + 1
            
        else:
            if (macdhist.iloc[IndexA] > 0 or
                IndexA > IndexB or
                macdhist.iloc[-1] > (0.8 * macdhist.iloc[IndexA]) or
                latest_close < A or
                latest_close > B):
                #logging.info ('MACD Histogram for Lower B index position is not Negative.Lower A index position is not lower than Higher B index Position,MACD Histogram Current close should be atleast 80% of MACD Hist of Lower A index positon : Exit BAD STOCK 10')
                return 1

            prince618 = round((((38.2*A)+(61.8*B))/100),2)
            price50 = round(((A+B)/2),2)
            #logging.info('price50  : {}'.format(price50))
            price382 = round((((61.8*A)+(38.2*B))/100),2)
            #logging.info('price38.2  : {}'.format(price382))
            price236 = round((((76.4*A)+(23.6*B))/100),2)
            #logging.info('price23.6  : {}'.format(price236))
            price114 = round((((88.6*A)+(11.4*B))/100),2)
            #logging.info('price11.4  : {}'.format(price114))   

            
            if (latest_close > price50 or
                latest_low < price114):
                #logging.info ('First Low Stock not within 50 to 11.4 range : Exit BAD STOCK 11')
                return 1
            
            stock_low_temp1 = self.stock_low[IndexB:]
            #logger.info('INFO stock_low_temp1',stock_low_temp1)
            LowestFromBtoRecent, LowestFromBtoRecentIndex = self.lowestLow(stock_low_temp1)
            #logger.info('INFO LowestFromBtoRecent',LowestFromBtoRecent)
            #logger.info('INFO LowestFromBtoRecentIndex',LowestFromBtoRecentIndex)
          
            if (LowestFromBtoRecent < price114):
                #logging.info ('First Low LowestFromBtoRecent: BAD STOCK 7 {}'.format(LowestFromBtoRecent))
                return 1
            '''
            #Screen nearning stocks
            if (latest_close > (1.05*price382) or
                latest_close > (1.05*price236) or
                latest_close > (1.05*price114)):
                #logging.info ('First Low:  Stock not nearing purchasing AREA : Exit BAD STOCK 11')
                return 1
            '''
            logging.info ('FIRST LOW : GOOD STOCK ZONE')
            # Get currency and exchange from symbol
            currency = "USD"
            exchange = "SMART"
            if symbol.endswith(".NS"):
                currency = "INR"
                exchange = "NSE"
            elif symbol.endswith(".L"):
                currency = "GBP"
                exchange = "LSE"
            elif symbol.endswith(".DE"):
                currency = "EUR"
                exchange = "XETRA"
            elif symbol.startswith("^"):
                exchange = "INDEX"
            
            # Calculate SMAs
            sma21_temp = self.movingAverage(stock_close, 21) if len(stock_close) > 21 else [0]
            sma50_temp = self.movingAverage(stock_close, 50) if len(stock_close) > 50 else [0]
            sma200_temp = self.movingAverage(stock_close, 200) if len(stock_close) > 200 else [0]
            sma21 = round(sma21_temp[-1], 2) if len(sma21_temp) > 0 else 0
            sma50 = round(sma50_temp[-1], 2) if len(sma50_temp) > 0 else 0
            sma200 = round(sma200_temp[-1], 2) if len(sma200_temp) > 0 else 0
            
            tempoutput = [timeframe,symbol,prince618,price50,price382,price236,price114,latest_close,B,A,"HOT",sma21,sma50,sma200,currency,exchange]
            #logging.info('self.tempoutput',tempoutput)
            self.output.append([0] * len(tempoutput))  #Create memory for 2 dimentional list before assinging
            for i in range(len(tempoutput)):                                        
                self.output[self.count][i] = tempoutput[i]            
            #logging.info('self.output {}'.format(self.output))            
            self.count = self.count + 1        
        return self.output

           
           
    @iswrapper
    def error(self, req_id, code, msg):
        self.code = code
        #logging.info('Error {}: {}'.format(code, msg))


if __name__ == '__main__':
    cd = CheckHiddenDivergence()
    cd.Check_Hidden_Divergence()
    
                                      

import ccxt
import time
import datetime
import pytz
import simplejson as json
import sys

class Order_info():
    
    def __init__(self,order_id=0,n=0):
        self.id=order_id
        self.n=n
        
class GridTrader():
    
    def __init__(self,file='setting.json'):

        info=GridTrader.read_setting(file)
        self.logfile=info['LOGFILE']
        
        if len(info['sub_account']) > 0:
            self.exchange  = ccxt.ftx({
                'verbose': False,
                'apiKey': f"{info['apiKey']}",
                'secret': f"{info['secret']}",
                'enableRateLimit': True,
                'headers': {'FTX-SUBACCOUNT': f"{info['sub_account']}"}
                })
        else:
            self.exchange  = ccxt.ftx({
                'verbose': False,
                'apiKey': f"{info['apiKey']}",
                'secret': f"{info['secret']}",
                'enableRateLimit': True
                })

        self.n=info['grid_level']

        self.amount=info['amount']

        self.market=info['symbol']
        self.prof=info['interval_prof']
        self.start_price=0

        self.startTime = time.time()

        self.vol = {'sell':0,'buy':0}
        self.val = {'sell':0,'buy':0}

        self.fee = {'coin':0.0,'fiat':0.0}
        self.liquidity = {'maker':0.0,'taker':0.0}
        self.track=[]

    def send_request(self,task,input1=None,input2=None):
        tries = 5
        for i in range(tries):
            try:
                if task == "get_last_price":
                    ticker =self.exchange.fetch_ticker(self.market)
                    return ticker['last']

                elif task == "get_order":
                    return self.exchange.fetch_order(input1)["info"]

                elif task == "place_order":
                    #send_request(self,task,input1=side,input2=price)
                    side = input1
                    price = input2
                    orderid=0
                    if side =="buy":
                        orderid = self.exchange.create_order(symbol=self.market,type='limit',side=side,price=price,amount=self.amount)["id"]
                    else:
                        orderid = self.exchange.create_order(symbol=self.market,type='limit',side=side,price=price,amount=self.amount)["id"]
                    return orderid

                elif task == 'cancel_order':
                    return self.exchange.cancel_order(id=input1)

                elif task == 'cancel_all_orders':
                    return self.exchange.cancel_all_orders(symbol=self.market)

                elif task == 'get_order_history':
                    history = self.exchange.fetch_my_trades(symbol=self.market,limit=50)
                    return history

                else:
                    return None

            except ccxt.NetworkError as e:
                if i < tries - 1: # i is zero indexed
                    self.log("NetworkError , try last "+str(i) +"chances" + str(e))
                    time.sleep(1+i)
                    continue
                else:
                    self.log(str(e))
                    raise
            except ccxt.ExchangeError as e:
                if i < tries - 1: # i is zero indexed
                    self.log(str(e))
                    time.sleep(0.5)
                    continue
                else:
                    self.log(str(e))
                    raise
            break
        
    def grid_init(self):
        
        self.send_request(task='cancel_all_orders')
        self.start_price=self.send_request(task='get_last_price')
        
        self.order_list = [[],[]] # ['buy','sell']

        for i in range(2):
            for j in range(1,self.n+1):
                price = self.start_price + (2*i-1)*j*self.prof
                orderId=self.send_request(task='place_order',input1=['buy','sell'][i],input2=price)
                self.order_list[i].append(Order_info(order_id=orderId,n=j))
            
    def loop_job(self):

        for i in range(2):
            for order in self.order_list[i]:
                info=self.send_request(task='get_order',input1=order.id)
                if info['status'] == 'closed' :
                    self.track.append(str(order.id))
                    self.vol[['buy','sell'][i]] += float(info['price']) * self.amount
                    self.val[['buy','sell'][i]] += self.amount
                    price = self.start_price + (2*i-1) * (order.n-1) * self.prof 
                    orderId=self.send_request(task='place_order',input1=['buy','sell'][1-i],input2=price)
                    self.order_list[1-i].append(Order_info(order_id=orderId,n=1-order.n))
                    self.order_list[i].remove(order)
                    msg=f"{['buy','sell'][i]} at {self.start_price+(2*i-1)*(order.n)*self.prof }, place new {['buy','sell'][1-i]} at {price}."
                    self.log(msg)
                    
            self.order_list[i] = sorted(self.order_list[i], key = lambda x : x.n)

            while len(self.order_list[i]) < self.n:
                price = self.start_price + (2*i-1) * (self.order_list[i][-1].n+1) * self.prof 
                orderId=self.send_request(task='place_order',input1=['buy','sell'][i],input2=price)
                self.order_list[i].append(Order_info(order_id=orderId,n=self.order_list[i][-1].n+1))
                msg=f"Enlarge grid for {['buy','sell'][i]} at {price}"
                self.log(msg)

            while len(self.order_list[i]) > 2*self.n :
                self.send_request(task='cancel_order',input1=self.order_list[i][-1].id)
                self.order_list[i].pop()
                msg=f"Cancel order for {['buy','sell'][i]} at {self.start_price+(2*i-1)*self.order_list[i][-1].n}"
                self.log(msg)

        order_history = self.send_request(task='get_order_history')
        order_info = [x['info'] for x in order_history if x['info']['orderId'] in self.track]

        for info in order_info:

            self.liquidity[info['liquidity']] += 1.0

            if info['feeCurrency'] == 'USD':
                self.fee['fiat'] += float(info['fee'])
            else:
                self.fee['coin'] += float(info['fee'])

            self.track.remove(info['orderId'])

    def log(self,msg,withTime=True):
        timestamp=datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime("%b %d %Y %H:%M:%S, ")
        try:
            f = open(f"{self.logfile}", "a")
            if withTime :
                f.write(timestamp + msg + "\n")
            else:
                f.write(msg + "\n")
            f.close()
        except:
            pass

    @staticmethod
    def read_setting(file='setting.json'):
        with open(file) as json_file:
            return json.load(json_file)

    def log_trading_info(self):
        coin = self.market[:self.market.find('/')]
        fiat = self.market[self.market.find('/')+1:]
        self.log("##########.Trading Info.##########")
        self.log(f"Trade balance: {self.vol['sell']-self.vol['buy']:+.2f} {fiat}, {self.val['buy']-self.val['sell']:+.4f} {coin}",withTime=False)
        trade_return=self.prof*min(self.val['buy'],self.val['sell'])/int(time.time()-self.startTime)*86400
        self.log(f"Return: {self.prof*min(self.val['buy'],self.val['sell']):.4f} {fiat}, {trade_return:.4f} {fiat}/Day",withTime=False)
        self.log(f"Volume: {(self.vol['buy']+self.vol['sell']):.2f} {fiat}, {(self.vol['buy']+self.vol['sell'])/int(time.time()-self.startTime)*86400 :.2f} {fiat}/Day",withTime=False)
        self.log(f"Maker ratio: {self.liquidity['maker']/max(self.liquidity['maker']+self.liquidity['taker'],1)*100:.2f}%, Total: {self.liquidity['maker']+self.liquidity['taker']:.0f}",withTime=False)
        self.log(f"Fee: {self.fee['fiat']:.8f} {fiat}, {self.fee['coin']:.8f} {coin}",withTime=False)
        self.log("##########.##########.##########.##########.##########",withTime=False)

    @staticmethod
    def start(trader):
        while True:
            try:
                trader.grid_init()
                startTime = time.time()
                while True:
                    if int(time.time()-startTime) > 20 :
                        trader.log_trading_info()
                        startTime = time.time()
                    trader.loop_job()
                    time.sleep(0.5)
            except:
                continue

if __name__ == '__main__':
    if len(sys.argv) > 1:
        GridTrader.start(trader=GridTrader(file=f'{sys.argv[1]}'))
    else:
        GridTrader.start(trader=GridTrader())


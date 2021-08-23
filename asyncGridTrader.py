import ccxtpro
import asyncio
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
            self.exchange  = ccxtpro.ftx({
                'verbose': False,
                'apiKey': f"{info['apiKey']}",
                'secret': f"{info['secret']}",
                'enableRateLimit': True,
                'headers': {'FTX-SUBACCOUNT': f"{info['sub_account']}"}
                })
        else:
            self.exchange  = ccxtpro.ftx({
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
        self.maxn = [0,0]

        self.fee = {'coin':0.0,'fiat':0.0}
        self.liquidity = {'maker':0.0,'taker':0.0}
        self.track=[]

    async def send_request(self,task,input1=None,input2=None,tries=0):
        tries=5
        for i in range(tries):
            try:
                if task == "get_last_price":
                    ticker = await self.exchange.fetch_ticker(self.market)
                    return ticker['last']

                elif task == "get_order":
                    info = await self.exchange.fetch_order(input1)
                    return info["info"]

                elif task == "place_order":
                    order = await self.exchange.create_order(symbol=self.market,type='limit',side=input1,price=input2,amount=self.amount)
                    return order["id"]

                elif task == 'cancel_order':
                    await self.exchange.cancel_order(id=input1)
                    return None

                elif task == 'cancel_all_orders':
                    await self.exchange.cancel_all_orders(symbol=self.market)
                    return None

                elif task == 'get_order_history':
                    history = await self.exchange.fetch_my_trades(symbol=self.market,limit=50)
                    return history

                else:
                    return None

            except ccxtpro.NetworkError as e:
                if i < tries - 1: # i is zero indexed
                    self.log("NetworkError, try last "+str(tries-i)+" chances, " + str(e))
                    if i==0:
                        time.sleep(self.exchange.rateLimit / 1000 )
                    else:
                        await asyncio.sleep(1+(i-1)*2)
                    continue
                else:
                    self.log(str(e))
                    raise

            except ccxtpro.ExchangeError as e:
                if i < tries - 1: # i is zero indexed
                    self.log(str(e))
                    await asyncio.sleep(1)
                    continue
                else:
                    self.log(str(e))
                    raise

            break

    async def grid_init_job(self,i,j):
        price = self.start_price + (2*i-1)*j*self.prof
        orderId= await self.send_request(task='place_order',input1=['buy','sell'][i],input2=price)
        self.order_list[i].append(Order_info(order_id=orderId,n=j))
        self.log(f"Init: Place {['buy','sell'][i]} at {price}")

    async def grid_init(self):
        
        await self.send_request(task='cancel_all_orders')
        self.start_price= await self.send_request(task='get_last_price')
        self.order_list = [[],[]] # ['buy','sell']

        tasks=[]
        for j in range(1,self.n+1):
            for i in range(2):
                tasks.append( asyncio.create_task(self.grid_init_job(i=i,j=j)) )
                
        await asyncio.gather(*tasks)

        self.maxn = [ self.n, self.n ]

    async def grid_loop_job(self,i,order):

        info= await self.send_request(task='get_order',input1=order.id)
        
        if info['status'] == 'closed' :
            self.track.append(str(order.id))
            self.vol[['buy','sell'][i]] += float(info['price']) * self.amount
            self.val[['buy','sell'][i]] += self.amount
            price = self.start_price + (2*i-1) * (order.n-1) * self.prof 
            orderId=await self.send_request(task='place_order',input1=['buy','sell'][1-i],input2=price)
            self.order_list[1-i].append(Order_info(order_id=orderId,n=1-order.n))
            self.order_list[i].remove(order)
            msg=f"{['buy','sell'][i]} at {self.start_price+(2*i-1)*(order.n)*self.prof }, place new {['buy','sell'][1-i]} at {price}."
            self.log(msg)

    async def grid_loop_job_fee(self):

        order_history = await self.send_request(task='get_order_history')
        order_info = [x['info'] for x in order_history if x['info']['orderId'] in self.track]

        for info in order_info:

            self.liquidity[info['liquidity']] += 1.0

            if info['feeCurrency'] == 'USD':
                self.fee['fiat'] += float(info['fee'])
            else:
                self.fee['coin'] += float(info['fee'])

            self.track.remove(info['orderId'])

    async def grid_loop(self):

        tasks=[]
        for i in range(2):
            for order in self.order_list[i]:
                tasks.append( asyncio.create_task(self.grid_loop_job(i=i,order=order)) )
            
        await asyncio.gather(*tasks)
        await self.grid_loop_job_fee()
        await self.grid_check2()

    # async def grid_check_job1(self,i,n):
    #     price = self.start_price + (2*i-1) * n * self.prof 
    #     orderId=await self.send_request(task='place_order',input1=['buy','sell'][i],input2=price)
    #     self.order_list[i].append(Order_info(order_id=orderId,n=n))
    #     msg=f"Enlarge grid for {['buy','sell'][i]} at {price}"
    #     self.log(msg)
    #     self.maxn[i] = n

    # async def grid_check_job2(self,i,order):
    #     await self.send_request(task='cancel_order',input1=order.id)
    #     msg=f"Cancel order for {['buy','sell'][i]} at {self.start_price+(2*i-1)*order.n}"
    #     self.log(msg)    
    #     self.order_list[i].remove(order)
    #     self.maxn[i] = order.n-1
                    
    # async def grid_check(self):

    #     tasks=[]
    #     for i in range(2):

    #         self.order_list[i] = sorted(self.order_list[i], key = lambda x : x.n)
    #         maxn=self.maxn[i]
    #         num=len(self.order_list[i])

    #         for j in range(self.n-num):
    #             tasks.append( asyncio.create_task(self.grid_check_job1(i=i,n=maxn+j+1)) )

    #         for j in range(num-2*self.n):
    #             tasks.append( asyncio.create_task(self.grid_check_job2(i=i,order=self.order_list[i][num-j-1])) )

    #     await asyncio.gather(*tasks)

    async def grid_check2(self):

        for i in range(2):

            self.order_list[i] = sorted(self.order_list[i], key = lambda x : x.n)
            
            while len(self.order_list[i]) < self.n:
                price = self.start_price + (2*i-1) * (self.maxn[i]+1) * self.prof 
                orderId= await self.send_request(task='place_order',input1=['buy','sell'][i],input2=price)
                self.order_list[i].append(Order_info(order_id=orderId,n=self.maxn[i]+1))
                msg=f"Enlarge grid for {['buy','sell'][i]} at {price}"
                self.log(msg)
                self.maxn[i] += 1

            while len(self.order_list[i]) > 2*self.n:
                await self.send_request(task='cancel_order',input1=self.order_list[i][-1].id)
                self.order_list[i].pop()
                msg=f"Cancel order for {['buy','sell'][i]} at {self.start_price+(2*i-1)*self.order_list[i][-1].n}"
                self.log(msg)
                self.maxn[i] -= 1

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

    async def run(self):
        await self.grid_init()
        startTime = time.time()
        while True:
            if int(time.time()-startTime) > 20 :
                self.log_trading_info()
                startTime = time.time()
            await self.grid_loop()
        await self.exchange.close()

    @staticmethod
    def start(trader):
        while True:
            try:
                asyncio.get_event_loop().run_until_complete(trader.run())
            except:
                continue

if __name__ == '__main__':
    if len(sys.argv) > 1:
        GridTrader.start(trader=GridTrader(file=f'{sys.argv[1]}'))
    else:
        GridTrader.start(trader=GridTrader())

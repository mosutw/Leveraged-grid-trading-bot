import sys
import time
import datetime
import asyncio
import pytz
from GridTrader import GridTrader
from db_connector import db_connector

class GridTrader_with_db(GridTrader):

    def __init__(self, file='setting.json'):

        super().__init__(file=file)

        info=GridTrader.read_setting(file=file)
        self.TableName=info['db_table_name']
        self.db=db_connector(hostname=info['db_host'],user=info['db_user'],passwd=info["db_passwd"],database=info['db_database'])

        self.db.execute(f'CREATE TABLE IF NOT EXISTS {self.TableName}(\
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,\
            sell_vol TEXT NOT NULL, buy_vol TEXT NOT NULL,\
            sell_val TEXT NOT NULL, buy_val TEXT NOT NULL,\
            maker BIGINT UNSIGNED NOT NULL, taker BIGINT UNSIGNED NOT NULL,\
            fiat TEXT NOT NULL, coin TEXT NOT NULL,\
            time TEXT NOT NULL, date TEXT NOT NULL,\
            e_day INT NOT NULL, e_hour INT NOT NULL, e_min INT NOT NULL, e_sec INT NOT NULL)')

        tmp=self.db.execute(f"SELECT * from {self.TableName} ORDER BY id DESC LIMIT 1")

        if len(tmp) > 0:

            self.vol['sell'] = float(tmp[0][1])
            self.vol['buy']  = float(tmp[0][2])

            self.val['sell'] = float(tmp[0][3])
            self.val['buy']  = float(tmp[0][4])

            self.liquidity['maker'] = float(tmp[0][5])
            self.liquidity['taker'] = float(tmp[0][6])

            self.fee['fiat'] = float(tmp[0][7])
            self.fee['coin'] = float(tmp[0][8])

            self.etime = float(tmp[0][11])*86400+float(tmp[0][12])*3600+float(tmp[0][13])*60+float(tmp[0][14])

        else:

            self.etime = 0.0

    def log_trading_info(self):
        coin = self.market[:self.market.find('/')]
        fiat = self.market[self.market.find('/')+1:]
        self.log("##########.Trading Info.##########")
        self.log(f"Trade balance: {self.vol['sell']-self.vol['buy']:+.2f} {fiat}, {self.val['buy']-self.val['sell']:+.4f} {coin}",withTime=False)
        trade_return=self.prof*min(self.val['buy'],self.val['sell'])/int(time.time()-self.startTime+self.etime)*86400
        self.log(f"Return: {self.prof*min(self.val['buy'],self.val['sell']):.4f} {fiat}, {trade_return:.4f} {fiat}/Day",withTime=False)
        self.log(f"Volume: {(self.vol['buy']+self.vol['sell']):.2f} {fiat}, {(self.vol['buy']+self.vol['sell'])/int(time.time()-self.startTime)*86400 :.2f} {fiat}/Day",withTime=False)
        self.log(f"Maker ratio: {self.liquidity['maker']/max(self.liquidity['maker']+self.liquidity['taker'],1)*100:.2f}%, Total: {self.liquidity['maker']+self.liquidity['taker']:.0f}",withTime=False)
        self.log(f"Fee: {self.fee['fiat']:.8f} {fiat}, {self.fee['coin']:.8f} {coin}",withTime=False)
        self.log("##########.##########.##########.##########.##########",withTime=False)

        info=GridTrader_with_db.time_info(int(time.time()-self.startTime+self.etime))

        cmd=f'INSERT INTO {self.TableName}(sell_vol,buy_vol,sell_val,buy_val,maker,taker,fiat,coin,time,date,e_day,e_hour,e_min,e_sec) VALUES(\
            "{self.vol["sell"]:.4f}", "{self.vol["buy"]:.4f}",\
            "{self.val["sell"]:.4f}", "{self.val["buy"]:.4f}",\
            "{self.liquidity["maker"]:.1f}","{self.liquidity["taker"]:.1f}",\
            "{self.fee["fiat"]:.8f}","{self.fee["coin"]:.8f}",\
            "{datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%H:%M:%S")}",\
            "{datetime.datetime.now(pytz.timezone("Asia/Taipei")).strftime("%d/%m-%Y")}",\
            {info[0]},{info[1]},{info[2]},{info[3]})'

        self.db.execute(cmd)
        
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

    @staticmethod
    def time_info(x):
        day=0
        hour=0
        minu=0
        if x>86400:
                day=x//86400
                x-=day*86400
        if x>3600:
                hour=x//3600
                x-=hour*3600
        if x>60:
                minu=x//60
                x-=minu*60
        return (day,hour,minu,x)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        GridTrader_with_db.start(trader=GridTrader_with_db(file=f'{sys.argv[1]}'))
    else:
        GridTrader_with_db.start(trader=GridTrader_with_db())

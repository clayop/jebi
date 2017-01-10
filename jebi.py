import urllib.parse
import urllib.request
import hmac
import requests
import json
import time
import hashlib
import telegram
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config_jebi

def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))
 
class poloniex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

    def post_process(self, before):
        after = before
 
        # Add timestamps if there isnt one but is a datetime
        if('return' in after):
            if(isinstance(after['return'], list)):
                for x in range(0, len(after['return'])):
                    if(isinstance(after['return'][x], dict)):
                        if('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(createTimeStamp(after['return'][x]['datetime']))
                           
        return after
 
    def api_query(self, command, req={}):
 
        if(command == "returnTicker" or command == "return24Volume"):
            ret = urllib.request.urlopen('https://poloniex.com/public?command=' + command)
            return json.loads(ret.read().decode('utf-8'))
        elif(command == "returnOrderBook"):
            ret = urllib.request.urlopen('http://poloniex.com/public?command=' + command + '&currencyPair=' + str(req['currencyPair']))
            return json.loads(ret.read().decode('utf-8'))
        elif(command == "returnMarketTradeHistory"):
            ret = urllib.request.urlopen('http://poloniex.com/public?command=' + "returnTradeHistory" + '&currencyPair=' + str(req['currencyPair']))
            return json.loads(ret.read().decode('utf-8'))
        else:
            req['command'] = command
            req['nonce'] = int(time.time()*1000)
            post_data = urllib.parse.urlencode(req)
            post_data = post_data.encode('utf-8')
 
            sign = hmac.new(str.encode(self.Secret), post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.APIKey
            }
 
            ret = urllib.request.urlopen(urllib.request.Request('https://poloniex.com/tradingApi', post_data, headers))
            jsonRet = json.loads(ret.read().decode('utf-8'))
            return self.post_process(jsonRet)
 

    def returnOrderBook (self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})
 
    def returnMarketTradeHistory (self, currencyPair, start_time):
        return self.api_query("returnMarketTradeHistory", {'currencyPair': currencyPair, "start": start_time})
 
 
    # Returns all of your balances.
    # Outputs:
    # {"BTC":"0.59098578","LTC":"3.31117268", ... }
    def returnBalances(self):
        return self.api_query('returnBalances')
 
    # Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self,currencyPair):
        return self.api_query('returnOpenOrders',{"currencyPair":currencyPair})
 
 
    # Returns your trade history for a given market, specified by the "currencyPair" POST parameter
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # date          Date in the form: "2014-02-19 03:44:59"
    # rate          Price the order is selling or buying at
    # amount        Quantity of order
    # total         Total value of order (price * quantity)
    # type          sell or buy
    def returnTradeHistory(self,currencyPair):
        return self.api_query('returnTradeHistory',{"currencyPair":currencyPair})
 
    # Places a buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is buying at
    # amount        Amount of coins to buy
    # Outputs:
    # orderNumber   The order number
    def buy(self,currencyPair,rate,amount):
        return self.api_query('buy',{"currencyPair":currencyPair,"rate":rate,"amount":amount})
 
    # Places a sell order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is selling at
    # amount        Amount of coins to sell
    # Outputs:
    # orderNumber   The order number
    def sell(self,currencyPair,rate,amount):
        return self.api_query('sell',{"currencyPair":currencyPair,"rate":rate,"amount":amount})
 
    # Cancels an order you have placed in a given market. Required POST parameters are "currencyPair" and "orderNumber".
    # Inputs:
    # currencyPair  The curreny pair
    # orderNumber   The order number to cancel
    # Outputs:
    # succes        1 or 0
    def cancel(self,currencyPair,orderNumber):
        return self.api_query('cancelOrder',{"currencyPair":currencyPair,"orderNumber":orderNumber})
 
    # Immediately places a withdrawal for a given currency, with no email confirmation. In order to use this method, the withdrawal privilege must be enabled for your API key. Required POST parameters are "currency", "amount", and "address". Sample output: {"response":"Withdrew 2398 NXT."}
    # Inputs:
    # currency      The currency to withdraw
    # amount        The amount of this coin to withdraw
    # address       The withdrawal address
    # Outputs:
    # response      Text containing message about the withdrawal
    def withdraw(self, currency, amount, address):
        return self.api_query('withdraw',{"currency":currency, "amount":amount, "address":address})

    def withdrawmemo(self, currency, amount, address, memo):
        return self.api_query('withdraw',{"currency":currency, "amount":amount, "address":address, "paymentId":memo})



def polo_balance(target):
    bal = polo.api_query("returnBalances")
    res = bal[target]
    return res

def polo_orderbook(target):
    url = "http://poloniex.com/public?command=returnOrderBook"
    params = {"currencyPair" : target}
    timeout = 10
    r = requests.get(url = url, params = params, timeout = timeout)
    res = r.json()
    return res
            
def polo_price(sell_amount, buy_amount):
    polo_ob = polo_orderbook("BTC_BTS")
    ret = {"bid":{}, "ask":{}}

    bts_sum = 0
    btc_sum = 0
    if sell_amount == 0:
        ret["bid"]["price"] = float(polo_ob["bids"][0][0])
        ret["bid"]["amount"] = float(polo_ob["bids"][0][1])
    else:
        bid_p = float(polo_ob["bids"][0][0])
        bid_q = float(polo_ob["bids"][0][1])
        for i in range(0,20):
            bts_sum = bts_sum + float(polo_ob["bids"][i][1])
            btc_sum = btc_sum + float(polo_ob["bids"][i][1])*float(polo_ob["bids"][i][0])
            bid_new_p = btc_sum/bts_sum
            bid_new_q = bts_sum
            if bid_new_p < bt_buy_p * spread:
                break
            else:
                bid_p = bid_new_p
                bid_q = bid_new_q
                if bts_sum > sell_amount:
                    btc_amount = btc_sum - (bts_sum - sell_amount)*float(polo_ob["bids"][i][0])
                    bid_p = btc_amount/sell_amount
                    bid_q = sell_amount
                    break
        ret["bid"]["price"] = bid_p
        ret["bid"]["amount"] = bid_q

    bts_sum = 0
    btc_sum = 0
    if buy_amount == 0:
        ret["ask"]["price"] = float(polo_ob["asks"][0][0])
        ret["ask"]["amount"] = float(polo_ob["asks"][0][1])
    else:
        ask_p = float(polo_ob["asks"][0][0])
        ask_q = float(polo_ob["asks"][0][1])
        for i in range(0,20):
            bts_sum = bts_sum + float(polo_ob["asks"][i][1])
            btc_sum = btc_sum + float(polo_ob["asks"][i][1])*float(polo_ob["asks"][i][0])
            ask_new_p = btc_sum/bts_sum
            ask_new_q = bts_sum
            if ask_new_p > bt_sell_p / spread:
                break            
            else:
                ask_p = ask_new_p
                ask_q = ask_new_q
                if bts_sum > buy_amount:
                    btc_amount = btc_sum - (bts_sum - buy_amount)*float(polo_ob["asks"][i][0])
                    ask_p = btc_amount/buy_amount
                    ask_q = buy_amount
                    break
        ret["ask"]["price"] = ask_p
        ret["ask"]["amount"] = ask_q

    return ret

def polo_order_detect():
    ret = {}
    openod = polo.returnOpenOrders("BTC_BTS")
    if openod == []:
        return None
    else:
        ret["amount"] = float(openod[0]["amount"])
        ret["orderno"] = openod[0]["orderNumber"]
        return ret

def polo_trade():
    now = int(time.time())
    payload = {'start': now-60, 'end': now}    
    r = requests.get("https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_BTS", params=payload)
    res = r.json()
    return res

def bt_orderbook(target):
    url = "http://api.btc38.com/v1/depth.php"
    params = {"c": target, "mk_type": "cny"}
    headers = {"User-Agent":"curl/7.35.0","Accept":"*/*"}
    timeout = 10
    for i in range(2):
        try:
            r = requests.get(url=url, params=params, headers=headers, timeout=timeout)
            break
        except:
            pass
    res = r.json()
    return res

def bt_balance():
    stamp = int(time.time())
    mdt = bt_pub + "_" + bt_id + "_" + bt_skey + "_" + str(stamp)
    mdt = mdt.encode("utf-8")
    m = hashlib.md5()
    m.update(mdt)
    m = m.hexdigest()
    url = "http://api.btc38.com/v1/getMyBalance.php"
    headers = {"User-Agent":"curl/7.35.0","Accept":"*/*"}
    data = {}
    data["key"] = bt_pub
    data["time"] = stamp
    data["md5"] = m
    timeout = 10
    for i in range(3):
        try:
            r = requests.post(url=url, data=data, headers=headers, timeout=timeout)
            break
        except:
            pass
    ret = r.json()
    return ret

def bt_buy(quote, price, amount):
    stamp = int(time.time())
    mdt = bt_pub + "_" + bt_id + "_" + bt_skey + "_" + str(stamp)
    mdt = mdt.encode("utf-8")
    m = hashlib.md5()
    m.update(mdt)
    m = m.hexdigest()
    url = "http://api.btc38.com/v1/submitOrder.php"
    headers = {"User-Agent":"curl/7.35.0","Accept":"*/*"}
    data = {}
    data["key"] = bt_pub
    data["time"] = stamp
    data["md5"] = m
    data["type"] = 1
    data["price"] = str(price)
    data["amount"] = str(amount)
    data["coinname"] = quote
    data["mk_type"] = "cny"
    timeout = 10
    for i in range(3):
        try:
            r = requests.post(url=url, data=data, headers=headers, timeout=timeout)
            break
        except:
            pass
    ret = r
    return ret

def bt_sell(quote, price, amount):
    stamp = int(time.time())
    mdt = bt_pub + "_" + bt_id + "_" + bt_skey + "_" + str(stamp)
    mdt = mdt.encode("utf-8")
    m = hashlib.md5()
    m.update(mdt)
    m = m.hexdigest()
    url = "http://api.btc38.com/v1/submitOrder.php"
    headers = {"User-Agent":"curl/7.35.0","Accept":"*/*"}
    data = {}
    data["key"] = bt_pub
    data["time"] = stamp
    data["md5"] = m
    data["type"] = 2
    data["price"] = str(price)
    data["amount"] = str(amount)
    data["coinname"] = quote
    data["mk_type"] = "cny"
    timeout = 10
    for i in range(3):
        try:
            r = requests.post(url=url, data=data, headers=headers, timeout=timeout)
            break
        except:
            pass
    ret = r
    return ret

def bt_btc_withdraw(amount):
    browser.get('http://btc38.com/trade_en.html')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="header_login_text"]/a')))
    login = browser.find_element_by_xpath('//*[@id="header_login_text"]/a')
    login.click()
    browser.get('http://www.btc38.com/trade/trade_setaddr_en.html?coinname=btc')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="drawBalance"]')))
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="submitDrawBTN"]/a')))
    time.sleep(2)
    btc_amount = browser.find_element_by_xpath('//*[@id="drawBalance"]')     # Make sure poloniex address is on the top
    btc_amount.send_keys(str(amount))
    btc_submit = browser.find_element_by_xpath('//*[@id="submitDrawBTN"]/a')
    btc_submit.click()
    WebDriverWait(browser, 10).until(EC.alert_is_present())
    time.sleep(1)
    alert = browser.switch_to.alert
    time.sleep(1)
    alert.accept()

def bt_bts_withdraw(amount):
    browser.get('http://btc38.com/trade_en.html')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="header_login_text"]/a')))
    login = browser.find_element_by_xpath('//*[@id="header_login_text"]/a')
    login.click()
    browser.get('http://www.btc38.com/trade/trade_setaddr_en.html?coinname=bts')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="drawBalance"]')))
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="memo"]')))
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="submitDrawBTN"]/a')))
    time.sleep(2)
    bts_amount = browser.find_element_by_xpath('//*[@id="drawBalance"]')     # Make sure the Poloniex is on the top
    bts_amount.send_keys(str(amount))
    bts_memo = browser.find_element_by_xpath('//*[@id="memo"]')
    bts_memo.send_keys(config_jebi.polo_bts_memo)
    bts_submit = browser.find_element_by_xpath('//*[@id="submitDrawBTN"]/a')
    bts_submit.click()
    WebDriverWait(browser, 10).until(EC.alert_is_present())
    time.sleep(1)
    alert = browser.switch_to.alert
    time.sleep(1)
    alert.accept()

if __name__ == '__main__':
    bt_pub = config_jebi.bt_pub
    bt_id = config_jebi.bt_id
    bt_skey = config_jebi.bt_skey
    polo_sign = config_jebi.polo_sign
    polo_secret = config_jebi.polo_secret
    telegram_token = config_jebi.telegram_token
    polo = poloniex(polo_sign, polo_secret)
    bot = telegram.Bot(token=telegram_token)
    
    custom_keyboard = [["/report"], ["/price"], ["/pause"]]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
    start_msg = "Jebi: Starting at " + time.ctime()
    bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=start_msg, reply_markup=reply_markup)
    print("Jebi: Starting at " + time.ctime())
    last_update_id = bot.getUpdates()[-1].update_id
    msg_on = 1
    start_time = time.time()
    
    display = Display(visible=0, size=(800, 600))
    display.start()
    browser = webdriver.Firefox()
    browser.get('http://btc38.com/trade_en.html')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="header_login_text"]/a')))
    login = browser.find_element_by_xpath('//*[@id="header_login_text"]/a')
    login.click()
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="email"]')))
    fb_user = browser.find_element_by_xpath('//*[@id="email"]')
    fb_user.send_keys(config_jebi.fb_user)
    fb_pwd = browser.find_element_by_xpath('//*[@id="pass"]')
    fb_pwd.send_keys(config_jebi.fb_pwd)
    fb_login = browser.find_element_by_xpath('//*[@id="loginbutton"]')
    fb_login.click()
    
    #body = browser.find_element_by_tag_name("body")
    #print(body.text)
    
    spread = 1.008
    err_i = 0
    pause = 0
    bthigh = 0
    polohigh = 0
    
    bt_bal = bt_balance()
    bt_bts_bal = float(bt_bal["bts_balance"])
    bt_btc_bal = float(bt_bal["btc_balance"])
    polo_all_balance = polo.api_query("returnBalances")
    polo_bts_bal = float(polo_all_balance["BTS"])
    polo_btc_bal = float(polo_all_balance["BTC"])
    start_btc_bal = 9        # bt_btc_bal/1.01 + polo_btc_bal
    start_bts_bal = 400000   # bt_bts_bal/1.01 + polo_bts_bal
    before_w_btc_bal = bt_btc_bal/1.01 + polo_btc_bal
    before_w_bts_bal = bt_bts_bal/1.01 + polo_bts_bal
    
    polo_bid_p = 1
    polo_ask_p = 1
    bt_buy_p = 1
    bt_sell_p = 1
    
    while True:
        try:
            if pause == 0:
                bt_bal = bt_balance()
                bt_btc_bal = float(bt_bal["btc_balance"])
                bt_bts_bal = float(bt_bal["bts_balance"])
                polo_all_balance = polo.api_query("returnBalances")
                polo_btc_bal = float(polo_all_balance["BTC"])
                polo_bts_bal = float(polo_all_balance["BTS"])
                all_btc_bal = bt_btc_bal/1.01 + polo_btc_bal
                all_bts_bal = bt_bts_bal/1.01 + polo_bts_bal
                if bt_sell_p/polo_ask_p > polo_bid_p/bt_buy_p:
                    higher = "BTC38"
                else:
                    higher = "Poloniex"
        
                if all_btc_bal > before_w_btc_bal*0.8:
                    btc_transfer_bal = 0
                    if polo_btc_bal/(bt_btc_bal+0.0001) < 0.2:
                        print("Start Balancing")
                        before_w_btc_bal = all_btc_bal
                        bt_btc_w_amount = (bt_btc_bal/1.01-all_btc_bal/2)*1.01
                        bt_btc_withdraw(format(bt_btc_w_amount, ".4f"))
                        msg = "Withdrew " + str(format(bt_btc_w_amount, ".4f")) + " BTC from BTC38"
                        print(msg)
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
                        btc_transfer_bal = btc_transfer_bal + bt_btc_w_amount/1.01
                    if bt_btc_bal/(polo_btc_bal+0.0001) < 0.2: 
                        print("Start Balancing")
                        before_w_btc_bal = all_btc_bal
                        polo_btc_w_amount = polo_btc_bal - all_btc_bal/2
                        polo.withdraw("BTC", format(polo_btc_w_amount, ".4f"), config_jebi.bt_btc_address) 
                        msg = "Withdrew " + str(format(polo_btc_w_amount, ".4f")) + " BTC from Poloniex"
                        print(msg)
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
                        btc_transfer_bal = btc_transfer_bal + polo_btc_w_amount
                if all_bts_bal > before_w_bts_bal*0.8:
                    bts_transfer_bal = 0
                    if polo_bts_bal/(bt_bts_bal+0.0001) < 0.1: 
                        print("Start Balancing")
                        before_w_bts_bal = all_bts_bal
                        bt_bts_w_amount = (bt_bts_bal/1.01-all_bts_bal/6)*1.01
                        bt_bts_withdraw(format(bt_bts_w_amount, ".0f"))
                        msg = "Withdrew " + str(format(bt_bts_w_amount, ".0f")) + " BTS from BTC38"
                        print(msg)
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
                        bts_transfer_bal = bts_transfer_bal + bt_bts_w_amount/1.01
                    if bt_bts_bal/(polo_bts_bal+0.0001) < 0.1:
                        print("Start Balancing")
                        before_w_bts_bal = all_bts_bal
                        polo_bts_w_amount = polo_bts_bal - all_bts_bal/6
                        polo.withdrawmemo("BTS", format(polo_bts_w_amount, ".0f"), "btc38-btsx-octo-72722", config_jebi.bt_id)   
                        msg = "Withdrew " + str(format(polo_bts_w_amount, ".0f")) + " BTS from Poloniex"
                        print(msg)
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
                        bts_transfer_bal = bts_transfer_bal + polo_bts_w_amount

                time.sleep(1)

                bt_bts_ob = bt_orderbook("bts")
                bt_btc_ob = bt_orderbook("btc")
                for i in range(10):
                    if float(bt_bts_ob["bids"][i][1]) > 1000:
                        bt_bts_bid_p = float(bt_bts_ob["bids"][i][0])
                        bt_bts_bid_q = float(bt_bts_ob["bids"][i][1])
                        break
                    else:
                        pass
                for i in range(10):
                    if float(bt_bts_ob["asks"][i][1]) > 1000:
                        bt_bts_ask_p = float(bt_bts_ob["asks"][i][0])
                        bt_bts_ask_q = float(bt_bts_ob["asks"][i][1])
                        break
                    else:
                        pass
                for i in range(10):
                    if float(bt_btc_ob["bids"][i][1]) > 1000:
                        bt_btc_bid_p = float(bt_btc_ob["bids"][i][0])
                        bt_btc_bid_q = float(bt_btc_ob["bids"][i][1])
                        break
                    else:
                        pass
                for i in range(10):
                    if float(bt_btc_ob["asks"][i][1]) > 1000:
                        bt_btc_ask_p = float(bt_btc_ob["asks"][i][0])
                        bt_btc_ask_q = float(bt_btc_ob["asks"][i][1])
                        break
                    else:
                        pass

                
                bt_btc_bid_p = float(bt_btc_ob["bids"][0][0])
                bt_btc_bid_q = float(bt_btc_ob["bids"][0][1])
                bt_btc_ask_p = float(bt_btc_ob["asks"][0][0])
                bt_btc_ask_q = float(bt_btc_ob["asks"][0][1])
                if bt_btc_bid_q < 0.02:
                    bt_btc_bid_p = float(bt_btc_ob["bids"][1][0])
                    bt_btc_bid_q = float(bt_btc_ob["bids"][1][1])
                if bt_btc_ask_q < 0.02:
                    bt_btc_ask_p = float(bt_btc_ob["asks"][1][0])
                    bt_btc_ask_q = float(bt_btc_ob["asks"][1][1])
                bt_buy_p = bt_bts_ask_p / bt_btc_bid_p   # e.g. 0.0302/2732 = 1241 sat
                bt_sell_p = bt_bts_bid_p / bt_btc_ask_p  # e.g. 0.0301/ 2744 = 1096 sat
                bt_buy_q = min(bt_bts_ask_q, bt_btc_bal/bt_buy_p, bt_btc_bid_q/bt_buy_p, polo_bts_bal)
                bt_sell_q = min(bt_bts_bid_q, bt_bts_bal, bt_btc_ask_q/bt_sell_p, polo_btc_bal/bt_sell_p)
                polo_ob = polo_orderbook("BTC_BTS")
                polo_p = polo_price(bt_buy_q, bt_sell_q) # BTC38 sell -> Polo buy
                polo_bid_p = polo_p["bid"]["price"]
                polo_ask_p = polo_p["ask"]["price"]
                bt_buy_q = min(bt_buy_q, polo_p["bid"]["amount"])
                bt_sell_q = min(bt_sell_q, polo_p["ask"]["amount"])        
        
                status_a = "BTC38 buy Poloniex sell: " + format(bt_buy_p, ".8f")+ " → " + format(polo_bid_p, ".8f") + "  " + format(polo_bid_p/bt_buy_p*100-100, ".2f")+"% / "
                status_b = "Poloniex buy BTC38 sell: " + format(polo_ask_p, ".8f") + " → " + format(bt_sell_p, ".8f") + "  " + format(bt_sell_p/polo_ask_p*100-100, ".2f")+"% / "
                price_log = status_a + format(bt_buy_q, ".0f") + " BTS    " + status_b + format(bt_sell_q, ".0f") + " BTS"
                print(price_log)

                if (polo_bid_p/bt_buy_p - 1) > (spread - 1) * 0.7:
                    polohigh = polohigh + 1
                    if polohigh > 5:
                        polohigh = 5
                else:
                    polohigh = polohigh - 1
                    if polohigh < 0:
                        polohigh = 0
                if (bt_sell_p/polo_ask_p - 1) > (spread - 1) * 0.7:
                    bthigh = bthigh + 1
                    if bthigh > 5:
                        bthigh = 5
                else:
                    bthigh = bthigh - 1
                    if bthigh < 0:
                        bthigh = 0
        
                if polo_bid_p > bt_buy_p * spread and bt_buy_q > 1000:
                    if polohigh >= 3:
                        polo.sell("BTC_BTS", polo_bid_p/1.02, (bt_buy_q/1.01)/(polo_bid_p/bt_buy_p))
                        print("Sold", format(bt_buy_q/(polo_bid_p/bt_buy_p), ".0f"),"BTS in Poloniex")
                        bt_sell("btc", format(bt_btc_bid_p/1.02, ".1f"), format(bt_buy_q*bt_buy_p, ".6f"))
                        print("Sold", format(bt_buy_q*bt_buy_p, ".4f"), "BTC in BTC38")
                        bt_cny_bal = bt_buy_q*bt_buy_p*(bt_btc_bid_p/1.01)
                        bt_cny_buy_q = bt_cny_bal/bt_bts_ask_p
                        bt_buy("bts", format(bt_bts_ask_p*1.02, ".4f"), format(bt_cny_buy_q/1.02, ".6f"))
                        print("Bought", format(bt_cny_buy_q/1.02, ".0f"), "BTS in BTC38")
                        time.sleep(1)
                        msg_on = 1
                        bt_bal = bt_balance()
                        bt_cny_bal = float(bt_bal["cny_balance"])
                        if bt_cny_bal > 1:
                            debug = bt_cny_buy_q/1.02, bt_cny_bal, bt_bts_ask_p
                            bt_buy("bts", format(bt_bts_ask_p*1.02, ".4f"), format(bt_cny_bal/bt_bts_ask_p/1.04, ".6f"))
                            print("Bought leftover")
                        msg = format(bt_buy_q, ".0f") + " BTS is bought in BTC38, sold in Poloniex at " + format(polo_bid_p/bt_buy_p*100-100, ".2f") + "%"
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
        
                if bt_sell_p > polo_ask_p * spread and bt_sell_q > 1000:
                    if bthigh >= 3:
                        polo.buy("BTC_BTS", polo_ask_p*1.02, bt_sell_q/(bt_sell_p/polo_ask_p))
                        print("Bought", format(bt_sell_q/(bt_sell_p/polo_ask_p), ".0f"),"BTS in Poloniex")
                        bt_sell("bts", format(bt_bts_bid_p/1.02, ".4f"), format(bt_sell_q/1.01, ".6f"))
                        print("Sold", format(bt_sell_q, ".0f"), "BTS in BTC38")
                        bt_cny_bal = (bt_sell_q/1.01)*(bt_bts_bid_p/1.01)
                        bt_cny_buy_q = bt_cny_bal/bt_btc_ask_p
                        bt_buy("btc", format(bt_btc_ask_p*1.02, ".1f"), format(bt_cny_buy_q/1.02, ".6f"))
                        print("Bought", format(bt_cny_buy_q/1.02, ".4f"), "BTC in BTC38")
                        time.sleep(1)
                        msg_on = 1
                        bt_bal = bt_balance()
                        bt_cny_bal = float(bt_bal["cny_balance"])
                        if bt_cny_bal > 1:
                            bt_buy("btc", format(bt_btc_ask_p*1.02, ".1f"), format(bt_cny_bal/bt_btc_ask_p/1.04, ".6f"))
                            print("Bought leftover")
                        msg = format(bt_sell_q, ".0f") + " BTS is bought in Poloniex, sold in BTC38 at " + format(bt_sell_p/polo_ask_p*100-100, ".2f") + "%"
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
    
            err_i = 0

            while True:
                updates = bot.getUpdates(offset=last_update_id, limit = 30)[-1]
                chat_id = updates.message.chat_id
                update_id = updates.update_id
                cmd = updates.message.text
                if update_id > last_update_id:
                    if (chat_id == YOUR_TELEGRAM_ID or chat_id == GROUP_ID) and cmd.split()[0] == "/start":
                        if chat_id == YOUR_TELEGRAM_ID:
                            custom_keyboard = [["/report"], ["/price"], ["/pause"]]
                        else:
                            custom_keyboard = [["/report"], ["/price"]]
                        reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
                        bot.sendMessage(chat_id=chat_id, text="Jebi", reply_markup=reply_markup)
                    if (chat_id == YOUR_TELEGRAM_ID or chat_id == ) and cmd.split()[0] == "/report":
                        btc_cmc = requests.get("http://coinmarketcap-nexuist.rhcloud.com/api/btc")
                        bts_cmc = requests.get("http://coinmarketcap-nexuist.rhcloud.com/api/bts")
                        btc_usd = float(btc_cmc.json()["price"]["usd"])
                        bts_usd = float(bts_cmc.json()["price"]["usd"])
                        start_usd_bal = start_btc_bal * btc_usd + start_bts_bal * bts_usd
                        transfer_log = ""
                        log_btc = str(format(all_btc_bal, ".3f"))
                        log_bts = str(format(all_bts_bal, ".0f"))
                        btc_usd_bal = (all_btc_bal - start_btc_bal) * btc_usd
                        bts_usd_bal = (all_bts_bal - start_bts_bal) * bts_usd
                        if btc_transfer_bal  + bts_transfer_bal > 0:
                            if all_btc_bal == before_w_btc_bal or all_bts_bal == before_w_bts_bal:
                                pass
                            else:
                                if btc_transfer_bal > 0:
                                    transfer_log = "On Transfer: " + format(btc_transfer_bal, ".3f") + " BTC\n"
                                    log_btc = str(format(all_btc_bal + btc_transfer_bal, ".3f"))
                                    btc_usd_bal = (all_btc_bal - start_btc_bal + btc_transfer_bal) * btc_usd
                                if bts_transfer_bal > 0:
                                    transfer_log = "On Transfer: " + format(bts_transfer_bal, ".0f") + " BTS\n"
                                    log_bts = str(format(all_bts_bal + bts_transfer_bal, ".0f"))
                                    bts_usd_bal = (all_bts_bal - start_bts_bal + bts_transfer_bal) * bts_usd
                                if btc_transfer_bal > 0 and bts_transfer_bal > 0:
                                    transfer_log = "On Transfer: " + format(btc_transfer_bal, ".3f") + " BTC  " + format(bts_transfer_bal, ".0f") + " BTS\n"
                                    log_btc = str(format(all_btc_bal + btc_transfer_bal, ".3f"))
                                    log_bts = str(format(all_bts_bal + bts_transfer_bal, ".0f"))
                                    btc_usd_bal = (all_btc_bal - start_btc_bal + btc_transfer_bal) * btc_usd
                                    bts_usd_bal = (all_bts_bal - start_bts_bal + bts_transfer_bal) * bts_usd
                        log_total_bal = "Total: " + log_btc + " BTC " + log_bts + " BTS\n"
                        bal_str = "BTC38: " + str(format(bt_btc_bal, ".3f")) + " BTC  " + str(format(bt_bts_bal, ".0f")) + " BTS\nPoloniex: " + str(format(polo_btc_bal, ".3f")) + " BTC  " + str(format(polo_bts_bal, ".0f")) + " BTS\n"
                        profit = format(btc_usd_bal + bts_usd_bal, ".2f")
                        profitper = format((btc_usd_bal + bts_usd_bal)/start_usd_bal*100, ".1f")
                        log = "Jebi " + time.strftime("%Y/%m/%d %H:%M:%S") + "\n" + log_total_bal + bal_str + transfer_log + "Profit : $" + profit + " (" + profitper + "%)" + "  Spread: " + str(spread)
                        bot.sendMessage(chat_id=chat_id, text=log)
                    if (chat_id == YOUR_TELEGRAM_ID or chat_id == GROUP_ID) and cmd.split()[0] == "/price":
                        price_log = status_a + format(bt_buy_q, ".0f") + " BTS\n" + status_b + format(bt_sell_q, ".0f") + " BTS"
                        bot.sendMessage(chat_id=chat_id, text=price_log)
                    if chat_id == YOUR_TELEGRAM_ID and cmd.split()[0] == "/pause":
                        pause = 1
                        print("Paused")
                        custom_keyboard = [["/report"], ["/price"], ["/resume"]]
                        reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
                        bot.sendMessage(chat_id=chat_id, text="Paused", reply_markup=reply_markup)
                    if chat_id == YOUR_TELEGRAM_ID and cmd.split()[0] == "/resume":
                        pause = 0
                        print("Resumed")
                        custom_keyboard = [["/report"], ["/price"], ["/pause"]]
                        reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
                        bot.sendMessage(chat_id=chat_id, text="Resumed", reply_markup=reply_markup)
                    if chat_id == YOUR_TELEGRAM_ID and cmd.split()[0] == "/spread":
                        try:
                            spread = float(cmd.split()[1])
                            if spread < 1.005:
                                spread = 1.005
                            spread_log = "Spread is now " + str(spread)
                            bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=spread_log)
                        except:
                            pass
                    if chat_id == YOUR_TELEGRAM_ID and cmd.split()[0] == "/startbtcbal":
                        old_start_btc_bal = start_btc_bal
                        start_btc_bal = float(cmd.split()[1])
                        log = "Start BTC balance was " + str(old_start_btc_bal) + " BTC and now " + str(start_btc_bal) + " BTC"
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=log)                        
                    if chat_id == YOUR_TELEGRAM_ID and cmd.split()[0] == "/startbtsbal":
                        old_start_bts_bal = start_bts_bal
                        start_bts_bal = float(cmd.split()[1])
                        log = "Start BTS balance was " + str(old_start_bts_bal) + " BTS and now " + str(start_bts_bal) + " BTS"
                        bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=log)  
                    
                    last_update_id = update_id
                time.sleep(2)
                if int(time.time()+15) % 30 >= 13 and int(time.time()+15) % 30 <= 17:
                    break
    
        except Exception as e:
            err_i = err_i +1
            print(e)
            msg = str(e)
            try:
                bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text=msg)
            except:
                pass
            sleep = int(time.time()) % 30   # sleep = int(time.time())%30
            time.sleep(30-sleep)
            if err_i >= 3:
                print("Continuous Errors")
                custom_keyboard = [["/report"], ["/price"], ["/resume"]]
                reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
                bot.sendMessage(chat_id=YOUR_TELEGRAM_ID, text="Continuous Errors. Paused", reply_markup=reply_markup)
                pause = 1
                err_i = 0

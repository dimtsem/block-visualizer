import requests
import pandas as pd
import numpy as np

class BitcoinAddress():

    def __init__(self, addrkey):
        self.addrkey = addrkey
        self.address_url = 'https://blockchain.info/rawaddr/'+self.addrkey
        data = requests.get(self.address_url)
        self.address = data.json()
        
    def n_tx(self):
        return self.address['n_tx']
    
    def tot_received(self):
        return self.address['total_received']
    
    def tot_sent(self):
        return self.address['total_sent']
    
    def get_nodes(self):
        txdata = [dict(self.address['txs'][k]) for k in range(min(int(self.n_tx()),50))]
        n_tx = len(txdata)
        txin = [[txdata[j]['inputs'][i]['prev_out']['addr'] 
                   for i in range(txdata[j]['vin_sz'])] for j in range(0,n_tx)]
        txout = [[txdata[j]['out'][i]['addr'] for i in range(txdata[j]['vout_sz']) 
                                        if 'addr' in txdata[j]['out'][i].keys()] for j in range(0,n_tx)]
        return {'Senders':txin,'Receivers':txout}
    
    def n_senders(self):
        Z = self.get_nodes()
        senlist = [z for y in [x for x in Z['Senders']] for z in y]
        L = list(set(senlist))
        if self.address in L:
            L.remove(self.address)
        return len(L)
    
    def n_receivers(self):
        Z = self.get_nodes()
        reclist = [z for y in [x for x in Z['Receivers']] for z in y]
        L = list(set(reclist))
        if self.address in L:
            L.remove(self.address)
        return len(L)
    
    def avg_timebtwtx(self):
        timelist = sorted([self.address['txs'][i]['time'] for i in range(min(int(self.n_tx()),50))])
        if len(timelist) == 1:
            return 0
        else:
            return sum([(timelist[i+1] - timelist[i]) for i in range(len(timelist) -1 )]) / max(1,len(timelist) -1)
        
    def max_timebtwtx(self): 
        timelist = sorted([self.address['txs'][i]['time'] for i in range(min(int(self.n_tx()),50))])
        if len(timelist) == 1:
            return 0
        else:
            return max([(timelist[i+1] - timelist[i]) for i in range(len(timelist) -1 )])
    
    def min_timebtwtx(self): 
        timelist = sorted([self.address['txs'][i]['time'] for i in range(min(int(self.n_tx()),50))])
        if len(timelist) == 1:
            return 0
        else:
            return min([(timelist[i+1] - timelist[i]) for i in range(len(timelist) -1 )])
    
    def stats(self):
        statnames = ['n_tx','tot_received','tot_sent','n_senders','n_receivers','avg_timebtwtx',
                     'max_timebtwtx','min_timebtwtx']
        return (self.n_tx(), self.tot_received(), 
                self.tot_sent(), self.n_senders(), 
                self.n_receivers(), self.avg_timebtwtx(), 
                self.max_timebtwtx(), self.min_timebtwtx())


class BitcoinBlock():
    
    def __init__(self,blockhash):
        try:
            latestblock_url = 'https://blockchain.info/rawblock/'+blockhash
            data = requests.get(latestblock_url)
            self.block = data.json() 
        except:
            print('Could not retrieve block - incorrect block hash?')
            
    def get_addresses(self):
        txdata = [dict(self.block['tx'][k]) for k in range(self.block['n_tx'])]
        n_tx = len(txdata)
        txin = [[txdata[j]['inputs'][i]['prev_out']['addr'] 
                   for i in range(txdata[j]['vin_sz'])] for j in range(1,n_tx)]
        txout = [[txdata[j]['out'][i]['addr'] for i in range(txdata[j]['vout_sz']) 
                                        if 'addr' in txdata[j]['out'][i].keys()] for j in range(0,n_tx)]
        return list(set([y for x in txin for y in x] + [y for x in txout for y in x]))



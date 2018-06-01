import requests
import pandas as pd
from collections import defaultdict
from sklearn.preprocessing import StandardScaler

import bokeh
from bokeh.io import show, output_file
from bokeh.models import Plot, Range1d, MultiLine, Circle, HoverTool, TapTool, BoxSelectTool, BoxAnnotation
from bokeh.models.tools import WheelZoomTool, PanTool
import holoviews as hv

from addrstats import BitcoinAddress

hv.extension('bokeh')
renderer = hv.renderer('bokeh')

class BTCAddressVisualization():



    def __init__(self, addresskey,depth,samplesize):
        self.address = addresskey
        self.depth = depth
        self.samplesize = samplesize

    #@staticmethod
    def get_wallet_data(self,wallethash):
        wallet_url = 'https://blockchain.info/rawaddr/'+wallethash
        data = requests.get(wallet_url)
        wallet = data.json()
        return pd.DataFrame(wallet)['txs']

    #@staticmethod
    def wallet_filter(self,wallethash,Z):
        for i in Z.index:
            if wallethash in Z['Receivers'][i]:
                Z['Receivers'][i] = [wallethash]
            elif wallethash in Z['Senders'][i]:
                Z['Senders'][i] = [wallethash]
            else:
                pass
        return Z
    
    #@staticmethod
    def get_nodes(self,wallet):
        txdata = self.get_wallet_data(wallet)
        n_tx = len(txdata)
        tx = pd.DataFrame(txdata.tolist())
        LL = [[tx['inputs'][j][i]['prev_out']['addr'] for i in range(tx['vin_sz'][j])] for j in range(0,n_tx)]
        txin = pd.Series(LL)
        LLL = [[tx['out'][j][i]['addr'] for i in range(tx['vout_sz'][j]) if 'addr' in tx['out'][j][i].keys()] for j in range(0,n_tx)]
        txout = pd.Series(LLL)
        txg_nodes = pd.DataFrame({'Senders':txin,'Receivers':txout})
        W = self.wallet_filter(wallet, txg_nodes)
        return W
    
    #@staticmethod
    def make_df(self,wallet):
        nodedata = self.get_nodes(wallet)
        return pd.DataFrame([(x,y) for i in nodedata.index
                         for x in nodedata['Senders'][i]
                         for y in nodedata['Receivers'][i]], columns=['Senders','Receivers'])


    #@staticmethod
    def make_df_ofdepth_sampling(self,wallet,depth,samplesize):
        visited = defaultdict(lambda : False)
        visited[wallet] = True
        df = self.make_df(wallet)
        df = df.sample(n = min(df.shape[0],samplesize))
        while depth > 0:
            for newwallet in list(set(df['Senders'].tolist()+df['Receivers'].tolist())):
                if not visited[newwallet]:
                    visited[newwallet] = True
                    try:
                        newdf = self.make_df(newwallet)
                        df = pd.concat([df,newdf.sample(n = min(newdf.shape[0],samplesize))])
                    except:
                        pass
            depth -= 1
        return df
    
    def make_df2(self,address):
        a = BitcoinAddress(address)
        tx = pd.DataFrame(a.address['txs'])
        n_tx = len(tx)
        LL = [[(tx['inputs'][j][i]['prev_out']['addr'],tx['inputs'][j][i]['prev_out']['value'])
           for i in range(tx['vin_sz'][j])] for j in range(0,n_tx)]
        LLL = [[(tx['out'][j][i]['addr'],tx['out'][j][i]['value']) for i in range(tx['vout_sz'][j])
                   if 'addr' in tx['out'][j][i].keys()] for j in range(0,n_tx)]
        df = pd.DataFrame([(x[0],x[1],y[0],y[1]) for i in range(len(LL)) for x in LL[i] for y in LLL[i]],
                             columns=['Sender','Sent','Recipient','Received'])
        df['Scaled_Sent'] = StandardScaler().fit_transform(pd.DataFrame(df['Sent']))
        df['Bitcoin Sent'] = df['Sent'] * 0.00000001
        return df[(df['Sender'] == address) | (df['Recipient'] == address)]


    def make_df2_ofdepth_sampling(self,wallet,depth,samplesize):
        visited = defaultdict(lambda : False)
        visited[wallet] = True
        df = self.make_df2(wallet)
        df = df.sample(n = min(df.shape[0],samplesize))
        while depth > 0:
            for newwallet in list(set(df['Sender'].tolist()+df['Recipient'].tolist())):
                if not visited[newwallet] and df.shape[0] < 500:
                    visited[newwallet] = True
                    try:
                        newdf = self.make_df2(newwallet)
                        df = pd.concat([df,newdf.sample(n = min(newdf.shape[0],samplesize))])
                    except:
                            pass
            depth -= 1
        return df

    def networkdf(self):
        dftoplot =  self.make_df2_ofdepth_sampling(self.address,self.depth,self.samplesize)
        dftoplot['origin'] = (dftoplot['Sender'] == self.address).astype(int) |\
            (dftoplot['Recipient'] == self.address).astype(int)
        #dftoplot['isoriginal'] = (dftoplot['Senders'] == self.address).astype(int) |\
        #                 (dftoplot['Receivers'] == self.address).astype(int)
        return dftoplot

    def plot(self):
        dftoplot = self.networkdf()
        nodelist = list(set(dftoplot['Senders'].tolist()+dftoplot['Receivers'].tolist()))
        node_labels = list(map(lambda addr: 1 if addr == self.address else 0, nodelist))
        nodedf = pd.DataFrame({'nodes':nodelist,'label':node_labels})

        padding = dict(x=(-1.2, 1.2), y=(-1.2, 1.2))

        node_info = hv.Dataset(nodedf, vdims='label')

        graph = hv.Graph((dftoplot,node_info)).redim.range(**padding)

        graphtoplot = graph.opts(plot=dict(width=800,height=600,\
                     color_index='label', edge_color_index='isoriginal',\
                     cmap='Set1', edge_cmap='viridis',inspection_policy='edges'))

        return renderer.get_plot(graphtoplot).state

    def plot2(self):
        dftoplot = self.networkdf()
        nodelist = list(set(dftoplot['Sender'].tolist()+dftoplot['Recipient'].tolist()))
        node_labels = list(map(lambda addr: 1 if addr == self.address else 0, nodelist))
        nodedf = pd.DataFrame({'nodes':nodelist,'label':node_labels})
        
        padding = dict(x=(-1.2, 1.2), y=(-1.2, 1.2))
        
        node_info = hv.Dataset(nodedf, vdims='label')

        graph = hv.Graph((dftoplot[['Sender','Recipient','Bitcoin Sent']], node_info)).redim.range(**padding)

        renderer = hv.renderer('bokeh')

        graphtoplot = graph.opts(plot=dict(width=800,height=600,xaxis=None,yaxis=None,\
                                   color_index='label', edge_color_index='Bitcoin Sent',inspection_policy='edges'),\
                                 style=dict(cmap=['blue','green'], edge_cmap='plasma',inspection_policy='edges'))
                                           
        return renderer.get_plot(graphtoplot).state

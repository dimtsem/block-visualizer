from flask import Flask, render_template, request, redirect
import requests
import pandas as pd
import networkx as nx
import pickle
from collections import defaultdict
#import matplotlib.pyplot as plt
#import matplotlib as mp
import numpy as np

from addrstats import BitcoinAddress, BitcoinBlock
from BTCAddressVisualization import BTCAddressVisualization

from sklearn import base
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from bokeh.io import show, output_file
from bokeh.models import Plot, Range1d, MultiLine, Circle, HoverTool, TapTool, BoxSelectTool, BoxAnnotation
from bokeh.models.graphs import from_networkx, NodesAndLinkedEdges, EdgesAndLinkedNodes
from bokeh.palettes import Spectral4
from bokeh.models.tools import WheelZoomTool, PanTool
from bokeh.plotting import figure, show, output_file
from bokeh.models import ColumnDataSource, Range1d, LabelSet, Label
from bokeh.embed import components

import holoviews as hv
hv.extension('bokeh')
renderer = hv.renderer('bokeh')
#%%opts Graph [width=800 height=800]
#%%opts Graph [color_index='label' edge_color_index='isoriginal'] (cmap='Set1' edge_cmap='viridis')

app = Flask(__name__)

###########################
#### Bokeh Figure Code ####
###########################

def create_figure(G,ntx):
    plot = Plot(plot_width=800, plot_height=600,
                x_range=Range1d(-1.1,1.1), y_range=Range1d(-1.1,1.1))
    #plot.title.text = "BTC Block Visualization"

    citation = Label(x=0, y=-20, x_units='screen', y_units='screen',
                text='This block contains '+str(ntx)+\
                 ' transactions between '+str(len(G.nodes()))+\
                 ' addresses. The most active address transacted with '+str(max(list(dict(G.degree()).values())))+\
                 ' addresses.',
                render_mode='css',
                border_line_color='red', border_line_alpha=1.0,
                background_fill_color='white', background_fill_alpha=1.0)

    #citation = Label(x=40, y=0, x_units='screen', y_units='screen',
    #             text='There were '+str(ntx)+' transactions total. The most active transactor was involved in '+str(max(list(dict(G.degree()).values())))+' transactions.',
    #             render_mode='css',
    #             border_line_color='black', border_line_alpha=1.0,
    #             background_fill_color='white', background_fill_alpha=1.0)

    plot.add_layout(citation)

    plot.add_tools(HoverTool(tooltips=None), TapTool(), BoxSelectTool(), WheelZoomTool(), PanTool())

    graph_renderer = from_networkx(G, nx.circular_layout, scale=1, center=(0,0))

    graph_renderer.node_renderer.glyph = Circle(size=4, fill_color=Spectral4[0])
    graph_renderer.node_renderer.selection_glyph = Circle(size=4, fill_color=Spectral4[2])
    graph_renderer.node_renderer.hover_glyph = Circle(size=4, fill_color=Spectral4[1])

    graph_renderer.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=3)
    graph_renderer.edge_renderer.selection_glyph = MultiLine(line_color=Spectral4[2], line_width=3)
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color=Spectral4[1], line_width=3)

    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = EdgesAndLinkedNodes()

    plot.renderers.append(graph_renderer)

    return plot

def create_transactor_figure(G):
    plot = Plot(plot_width=800, plot_height=600,
            x_range=Range1d(-1.1,1.1), y_range=Range1d(-1.1,1.1))
    plot.title.text = "Transactor Visualization"

    plot.add_tools(HoverTool(tooltips=None), TapTool(), BoxSelectTool(), WheelZoomTool(), PanTool())

    graph_renderer = from_networkx(G, nx.spring_layout, scale=1, center=(0,0))

    graph_renderer.node_renderer.glyph = Circle(size=4, fill_color=Spectral4[0])
    graph_renderer.node_renderer.selection_glyph = Circle(size=4, fill_color=Spectral4[2])
    graph_renderer.node_renderer.hover_glyph = Circle(size=4, fill_color=Spectral4[1])

    graph_renderer.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=3)
    graph_renderer.edge_renderer.selection_glyph = MultiLine(line_color=Spectral4[2], line_width=3)
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color=Spectral4[1], line_width=3)

    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = EdgesAndLinkedNodes()

    plot.renderers.append(graph_renderer)

    return plot


####################################
#### Wallet Data Retrieval Code ####
####################################

def get_wallet_data(wallethash):
    #w = str(wallethash)
    print(str(wallethash))
    wallet_url = str('https://blockchain.info/rawaddr/'+str(wallethash))
    data = requests.get(wallet_url).json()
    #wallet = data.json()
    return pd.DataFrame(data)['txs']

def wallet_filter(wallethash,Z):
    for i in Z.index:
      if wallethash in Z['Receivers'][i]:
        Z['Receivers'][i] = [wallethash]
      elif wallethash in Z['Senders'][i]:
        Z['Senders'][i] = [wallethash]
      else:
        pass
    return Z

def get_nodes(wallet):
    txdata = get_wallet_data(wallet)
    n_tx = len(txdata)
    tx = pd.DataFrame(txdata.tolist())
    LL = [[tx['inputs'][j][i]['prev_out']['addr'] for i in range(tx['vin_sz'][j])] for j in range(0,n_tx)]
    txin = pd.Series(LL)
    LLL = [[tx['out'][j][i]['addr'] for i in range(tx['vout_sz'][j]) if 'addr' in tx['out'][j][i].keys()] for j in range(0,n_tx)]
    txout = pd.Series(LLL)
    txg_nodes = pd.DataFrame({'Senders':txin,'Receivers':txout})
    W = wallet_filter(wallet, txg_nodes)
    return W

def get_interactors(wallet):
    Z = get_nodes(wallet)
    reclist = [z for y in [x for x in Z['Receivers']] for z in y]
    senlist = [z for y in [x for x in Z['Senders']] for z in y]
    return list(set(reclist+senlist))

def get_interactors_ofdepth(wallet,depth):
    if depth == 0:
      X = get_interactors(wallet)
      return X
    else: 
      Y = []
      for interactor in get_interactors_ofdepth(wallet, depth-1):
        Z = get_interactors(interactor)
        for w in Z:
          Y.append(w)
      return Y

def make_graph(nodedata):
    G = nx.MultiDiGraph()
    for i in nodedata.index:
      for x in nodedata['Senders'][i]:
        for y in nodedata['Receivers'][i]:
          G.add_edge(x,y)
    return G

def make_graph_ofdepth(wallet,depth):
    if depth == 0:
        try:  
            G = make_graph(get_nodes(wallet))
            return G
        except:
            G = nx.MultiDiGraph()
            return G
    else:
      G = make_graph_ofdepth(wallet,depth-1)
      for interactor in get_interactors_ofdepth(wallet, depth):
        try:
          nodedata = get_nodes(interactor)
          for i in nodedata.index:
            for x in nodedata['Senders'][i]:
              for y in nodedata['Receivers'][i]:
                G.add_edge(x,y)
        except:
          print('Could not retrieve data from wallet ', interactor)
    return G

def make_df(wallet):
    nodedata = get_nodes(wallet)
    return pd.DataFrame([(x,y) for i in nodedata.index
                         for x in nodedata['Senders'][i]
                         for y in nodedata['Receivers'][i]], columns=['Senders','Receivers'])

def make_df_ofdepth(wallet,depth):
    visited = defaultdict(lambda : False)
    visited[wallet] = True
    df = make_df(wallet)
    while depth > 0:
        for newwallet in list(set(df['Senders'].tolist()+df['Receivers'].tolist())):
            if not visited[newwallet]:
                visited[newwallet] = True
                df = pd.concat([df,make_df(newwallet)])
        depth -= 1
    return df

def make_df_ofdepth_sampling(wallet,depth,samplesize):
    visited = defaultdict(lambda : False)
    visited[wallet] = True
    df = make_df(wallet)
    df = df.sample(n = min(df.shape[0],samplesize))
    while depth > 0:
        for newwallet in list(set(df['Senders'].tolist()+df['Receivers'].tolist())):
            if not visited[newwallet]:
                visited[newwallet] = True
                try:
                    newdf = make_df(newwallet)
                    df = pd.concat([df,newdf.sample(n = min(newdf.shape[0],samplesize))])
                except:
                    pass
        depth -= 1
    return df


########################
#### Equality Tests #### 
########################

def get_nodes_nofilter(wallet):
    txdata = get_wallet_data(wallet)
    n_tx = len(txdata)
    tx = pd.DataFrame(txdata.tolist())
    LL = [[tx['inputs'][j][i]['prev_out']['addr'] for i in range(tx['vin_sz'][j])] for j in range(0,n_tx)]
    txin = pd.Series(LL)
    LLL = [[tx['out'][j][i]['addr'] for i in range(tx['vout_sz'][j]) if 'addr' in tx['out'][j][i].keys()] for j in range(0,n_tx)]
    txout = pd.Series(LLL)
    return pd.DataFrame({'Senders':txin,'Receivers':txout})

def equalitytest_simple(wallet1, wallet2):
    senders1 = get_nodes_nofilter(wallet1)['Senders']
    senders2 = get_nodes_nofilter(wallet2)['Senders']
    while True:
        for x in senders1:
            if wallet2 in x:
                return True
            else:
                pass
        for y in senders2:
            if wallet1 in y:
                return True
            else:
                pass
        break
    return False


###################
#### MAIN BODY ####
###################

@app.route('/')
def index():
  return render_template("index2.html")

@app.route('/blockplot')
def blockplot():
    blockhash = request.args.get("blockhash")
  
    if blockhash == 'latest':
      #Retrieve the latest bloc hash from the Blockchain.info API
      latesthash = 'https://blockchain.info/q/latesthash'
      r = requests.get(latesthash)
      lh = str(r.text)
      latestblock_url = 'https://blockchain.info/rawblock/'+lh
      data = requests.get(latestblock_url)
      block = data.json()
    else:
      try:
        latestblock_url = 'https://blockchain.info/rawblock/'+blockhash
        data = requests.get(latestblock_url)
        block = data.json()	
      except:
        print('We could not retrieve block - incorrect block hash?')
        return render_template('index2.html')
    #Convert the data into a DataFrame
    n_tx = int(block['n_tx'])
    txseries = pd.Series(block['tx'])
    tx = pd.DataFrame(txseries.tolist())
    LL = [[tx['inputs'][j][i]['prev_out']['addr'] for i in range(tx['vin_sz'][j])] for j in range(1,n_tx)]
    txin = pd.Series(LL)
    LLL = [[tx['out'][j][i]['addr'] for i in range(tx['vout_sz'][j]) if 'addr' in tx['out'][j][i].keys()] for j in range(0,n_tx)]
    txout = pd.Series(LLL)
    txin.loc[-1]= ['N/A']
    txin.index = txin.index + 1
    txin = txin.sort_index()
    txg_nodes = pd.DataFrame({'Senders':txin,'Receivers':txout})

    #Turn the DataFrame into a networkx directed multigraph
    G = nx.MultiDiGraph()
    for i in range(n_tx):
      for x in txg_nodes['Senders'][i]:
        for y in txg_nodes['Receivers'][i]:
          G.add_edge(x,y)

    plot = create_figure(G,n_tx)

    script, div = components(plot)
    return render_template("block_plot.html", script=script, div=div)

@app.route('/walletplot')
def walletplot():
    wallethash = request.args.get("wallethash")
    w = str(wallethash)
    plot = BTCAddressVisualization(w,2,20).plot2()
    script, div = components(plot)
    return render_template("wallet_plot.html", script=script, div=div)


@app.route('/equalityresult')
def equalityresult():
    wallet1 = request.args.get('wallethash1')
    wallet2 = request.args.get('wallethash2')
    if equalitytest_simple(wallet1,wallet2):
        return render_template('equalityresult.html', result='These wallets belong to the same entity')
    else:
        return render_template('equalityresult.html', result='These wallets do not belong to the same entity')

@app.route('/wallettype')
def wallettype():
    model = pickle.load(open('kmeans_classifier_addrsample_20.sav', 'rb'))
    address = request.args.get("address")
    print(address, type(address))
    
    #try:
    b = BitcoinBlock(address)
    blockaddresses = b.get_addresses()
    blockaddrval = b.get_addrval()
        #except:
        #return render_template('wallettype.html', result='Could not obtain address data')
    txbal = blockaddrval[0]
    txapp = blockaddrval[1]

    A = []
    for a in blockaddresses[0:35]:
        print('Getting data for ', a,'...')
        try:
            A.append((a,txapp[a],txbal[a],BitcoinAddress(a).stats()))
            print('...success')
        except:
            print('...failed')

    C = [(a[0],a[1],a[2]*0.00000001,model.predict([a[3]])[0]) for a in A]
    dfraw = pd.DataFrame(C,columns=['address','appearances','balance','cluster'])
    dftoplot = dfraw.groupby('cluster').sum()
    dftoplot['BTC'] = dftoplot['balance'] * 0.00000001
    dftoplot = dftoplot[['appearances','BTC']]

    padding = dict(x=(-1.2, 1.2), y=(-1.2, 1.2))

    data_app = list(zip(dftoplot.index,np.log(dftoplot['appearances'])))
    data_btc = list(zip(dftoplot.index,dftoplot['BTC']))
    bars_app = hv.Bars(data_app, hv.Dimension('Address Clusters'), 'Log(Appearances)').redim.range(**padding)
    bars_btc = hv.Bars(data_btc, hv.Dimension('Address Clusters'), 'BTC').redim.range(**padding)

    bars_app_plot = renderer.get_plot(bars_app.opts(plot=dict(width=400,height=300))).state
    bars_btc_plot = renderer.get_plot(bars_btc.opts(plot=dict(width=400,height=300))).state

    script1, div1 = components(bars_app_plot)
    script2, div2 = components(bars_btc_plot)

    return render_template("blockaddrtype_plot.html", script1=script1, div1=div1,\
                           script2=script2, div2=div2)



@app.route('/about')
def about():
  return render_template('about_simple.html')

if __name__ == '__main__':
  app.run(port=33507, debug=True)

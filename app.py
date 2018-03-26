from flask import Flask, render_template, request, redirect
import requests
import pandas as pd
import networkx as nx
from bokeh.io import show, output_file
from bokeh.models import Plot, Range1d, MultiLine, Circle, HoverTool, TapTool, BoxSelectTool, BoxAnnotation
from bokeh.models.graphs import from_networkx, NodesAndLinkedEdges, EdgesAndLinkedNodes
from bokeh.palettes import Spectral4
from bokeh.models.tools import WheelZoomTool, PanTool
from bokeh.plotting import figure, show, output_file
from bokeh.models import ColumnDataSource, Range1d, LabelSet, Label
from bokeh.embed import components


app = Flask(__name__)

def create_figure(G,ntx):
    plot = Plot(plot_width=800, plot_height=600,
                x_range=Range1d(-1.1,1.1), y_range=Range1d(-1.1,1.1))
    plot.title.text = "BTC Block Visualization"

    citation = Label(x=40, y=0, x_units='screen', y_units='screen',
                 text='There were '+str(ntx)+' transactions total. The most active transactor was involved in '+str(max(list(dict(G.degree()).values())))+' transactions.',
                 render_mode='css',
                 border_line_color='black', border_line_alpha=1.0,
                 background_fill_color='white', background_fill_alpha=1.0)

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


    output_file("block_plot.html")
    return plot

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/figure')
def figure():
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


@app.route('/about')
def about():
  return render_template('about.html')

if __name__ == '__main__':
  app.run(port=33507, debug=True)

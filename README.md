# Bitcoin Transaction Visualizer

An application, deployed on Heroku, that creates visualizations of blocks and addresses on the Bitcoin blockchain.

It is built on the flask-framework repo and all due credit for the architecture goes there.

## Current State

Everything runs nominally, except the fourth feature is only being run as a "toy version", in the absence of a backend, since streaming the data has proved too slow.

## Files and Folders

Procfile -- for Heroku

BTCAddressVisualization.py -- contains classes useful for visualization, used by app.py

addrstats.py -- contains classes for Bitcoin blocks and addresses tailored to the data as stored on Blockchain.info

app.py -- the main body of the application

condo-requirements -- for Heroku

kmeans_class* -- two serialized clustering models, to be used in app.py

requirements.txt -- for Heroku

runtime.txt -- for Heroku


**data** -- contains files that were used to scrape the data used in the analysis and also an expository notebook "Clustering Addresses on the Bitcoin Blockchain" explaining the ideas behind the application. 

**templates** -- contains the html templates for the application








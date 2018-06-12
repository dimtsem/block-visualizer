import requests
import time
import pandas as pd
import json
from addrstats import BitcoinBlock, BitcoinAddress

dayrange = 7
days = [int(round(int(round(time.time() * 1000)) - (n * 8.64e+7))) for n in range(dayrange)]

fracparameter = 0.01
intparameter = 3

blockhashes = {}
for day in days:
    try:
        last24hourblocks = requests.get('https://blockchain.info/blocks/'+str(day)+'?format=json').json()
        last24_blocklist = [x['hash'] for x in last24hourblocks['blocks']]
        blockhashes[day] = list(pd.DataFrame({'A':last24_blocklist})['A'].sample(n = intparameter))
    except:
        print('Could not obtain blocks for '+str(day))

sample = [x for y in blockhashes.values() for x in y]

addr_stats = []

for blockhash in sample:
    print('Scouring '+blockhash+ ' for addresses...')
    try:
        b = BitcoinBlock(blockhash)
        with open('block_'+blockhash+'.json','w') as f:
            json.dump(b.block,f)
        try:
            A = b.get_addresses()
            for addr in list(pd.DataFrame(A).sample(frac = 0.15)[0]):
                print('Getting data for '+addr+' ...')
                try:
                    a = BitcoinAddress(addr)
                    with open('address_'+a.addrkey+'.json','w') as f:
                        json.dump(a.address, f)  
                    addr_stats.append(BitcoinAddress(addr).stats())
                except:
                    print('...failed')
        except:
            print('...failed')
    except:
        print('...failed to obtain block')

with open('stats.txt','w') as f:
    f.write('\n'.join([' '.join(map(str,x)) for x in addr_stats]))


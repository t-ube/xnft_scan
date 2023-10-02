import { Client } from 'xrpl'

class LFTokenOffer {
  flags: number = 0;
  owner: string = '';
  amount: number = 0;
  nft_id: string = '';
  dest: string = '';
  ledgerIndex: string = '';
  
  set(flags: number, owner: string, amount: number, nft_id: string, dest: string, ledgerIndex: string) {
    this.flags = flags;
    this.owner = owner;
    this.amount = amount;
    this.nft_id = nft_id;
    this.dest = dest;
    this.ledgerIndex = ledgerIndex;
  }
}
  
  class NFTokenAcceptOffer {
    nft_id: string = '';
    ledger_index: number = 0;
    date: number = 0;
    sell: string = '';
    buy: string = '';
    amount: number = 0;
  
    debug_print() {
      console.log(this);
    }
  }
  
function get_accept_tx(data_dict: any): void {
  const accept_offers: NFTokenAcceptOffer[] = [];

  try {
    for (const transaction of data_dict.result.transactions) {
      const tx = transaction.tx;
      const meta = transaction.meta;
      const tx_type = tx.TransactionType;
      const ledger_index = tx.ledger_index;
      const date = tx.date;

      const buy = new LFTokenOffer();
      const sell = new LFTokenOffer();
      const offer = new NFTokenAcceptOffer();

      if (tx_type === 'NFTokenAcceptOffer') {
        if ('NFTokenSellOffer' in tx) {
          if ('AffectedNodes' in meta && 'TransactionResult' in meta) {
            if (meta.TransactionResult === 'tesSUCCESS') {
              const nodes = meta.AffectedNodes;
              for (const node of nodes) {
                if ('DeletedNode' in node) {
                  if ('FinalFields' in node.DeletedNode) {
                    if (node.DeletedNode.LedgerEntryType === 'NFTokenOffer') {
                      const fields = node.DeletedNode.FinalFields;
                      if (fields.Flags & 1) {
                        sell.set(fields.Flags, fields.Owner, fields.Amount, fields.NFTokenID, fields.Destination, node.DeletedNode.LedgerIndex);
                      } else if (fields.Flags === 0) {
                        buy.set(fields.Flags, fields.Owner, fields.Amount, fields.NFTokenID, fields.Destination, node.DeletedNode.LedgerIndex);
                      }
                    }
                  }
                }
              }
              if ('NFTokenBuyOffer' in tx) {
                if (sell.nft_id === buy.nft_id) {
                  offer.nft_id = sell.nft_id;
                  offer.ledger_index = ledger_index;
                  offer.date = date;
                  offer.sell = sell.owner;
                  offer.buy = buy.owner;
                  offer.amount = buy.amount;
                  accept_offers.push(offer);
                }
              } else {
                offer.nft_id = sell.nft_id;
                offer.ledger_index = ledger_index;
                offer.date = date;
                offer.sell = sell.owner;
                offer.buy = sell.dest;
                offer.amount = sell.amount;
                accept_offers.push(offer);
              }
            }
          }
        }
      }
    }

    for (const data of accept_offers) {
      data.debug_print();
    }
  } catch (error) {
    console.error("An error occurred:", error);
  }
}

async function main() {
  const client = new Client('wss://s2-clio.ripple.com:51233/')
  await client.connect()

  const response = await client.request({
      command: "nft_history",
      nft_id: "00082710E84B2279489BC610EA4B4F1C8553CEE6C7D1786FAACE82C500000029"
  })
  get_accept_tx(response)
  const jsonStr = JSON.stringify(response, null, 2)
  console.log(jsonStr)

  await client.disconnect()
  /*
  const fs = require('fs');
  fs.writeFile('output.json', jsonStr, 'utf8', function(err:any) {
      if (err) {
        console.log("An error occured while writing JSON Object to File.");
        return console.log(err);
      }
      console.log("JSON file has been saved.");
  });
  */
}

main()

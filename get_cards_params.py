import requests
#test card_params
#r = requests.get('https://docs.google.com/spreadsheet/ccc?key=18txrb4Md1OqMl23T3hDdOuQE8TXjEZVh9-6UdY4OSR4&output=csv')
#prod card_params
r = requests.get('https://docs.google.com/spreadsheet/ccc?key=1luWE-rUSclxTI_BX_QsHTXTduzpfKslRBrOM53di5Sg&output=csv')
assert r.status_code == 200, 'Wrong status code'
r.encoding = r.apparent_encoding

with open('cards_params.csv', 'w') as output_file:
     output_file.write(r.text)
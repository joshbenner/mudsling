import icmoney

# By declaring currencies, they are automatically registered.
pp = icmoney.Currency('pp', 'Platinum Piece', 10.0)
gp = icmoney.Currency('gp', 'Gold Piece', 1.0)
sp = icmoney.Currency('sp', 'Silver Piece', 0.1)
cp = icmoney.Currency('cp', 'Copper Piece', .01)

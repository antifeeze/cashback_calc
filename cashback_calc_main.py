from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os, csv, math, re, decimal
from decimal import *
from datetime import datetime, timedelta

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#getcontext().prec = 3
#getcontext().rounding = ROUND_DOWN
#number = Decimal("100.35")
#print(number.quantize(Decimal("1.00")))

def csv_import(file_path):
#    results = []
    with open(file_path, newline='') as f:
         reader = list(csv.reader(f))
    return reader

all_card_params = csv_import('card_params.csv')
card_names = [col[0] for col in all_card_params]

def file_upload(MccFile):
    if MccFile.filename == '':
       flash('No selected file')
    if MccFile:
       filename = secure_filename(MccFile.filename)
       MccFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

       file_path = app.config['UPLOAD_FOLDER'] + "/" + filename
       mcc_t = csv_import(file_path)

       #       for img in range(len(mcc_t)):
#           print (mcc_t[img], flush=True)
    return mcc_t


def card_profit_calc(StartDate, FinishDate, AdditionalCosts, card_params, mcc_t):

    cashback_total = 0
    spent_with_cashback = 0
    cashback_default = 0
    cashback_high_mcc = 0
    spent_no_cashback = 0

    no_mcc_list = card_params[6].split(", ")
    high_mcc_list = card_params[7].split(", ")
    if card_params[2]:
       high_perc = Decimal(card_params[2].replace("%", "").replace(",", "."))
    default_perc = Decimal(card_params[1].replace("%", "").replace(",", "."))
    #print (high_perc, flush=True)

    for i in range(len(mcc_t)):
        #print (str(i) + " | " + mcc_t[i][1], flush=True)
        mcc = mcc_t[i][0]

        if re.match("(^[\d]{4}$)", mcc) and mcc_t[i][1]:
           amount = Decimal(mcc_t[i][1].replace("−", "").replace("-", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))

           if card_params[4] == 'До 100':
              cashback_base = Decimal(math.floor(amount/100))
           elif card_params[4] == 'До 50':
                cashback_base = Decimal((math.floor(amount/50))/2)
           elif card_params[4] == 'Нет':
                cashback_base = Decimal(amount/100)

           if mcc in high_mcc_list:
              cashback_total = math.floor((cashback_base*high_perc*100)/100)+Decimal(cashback_total)
              cashback_high_mcc = math.floor((cashback_base*high_perc*100)/100)+Decimal(cashback_high_mcc)
              spent_with_cashback = amount+Decimal(spent_with_cashback)
           elif mcc in no_mcc_list:
                spent_no_cashback = amount+Decimal(spent_no_cashback)
           else:
               cashback_total = math.floor((cashback_base*default_perc*100)/100)+Decimal(cashback_total)
               cashback_default = math.floor((cashback_base*default_perc*100)/100)+Decimal(cashback_default)
               spent_with_cashback = amount+Decimal(spent_with_cashback)

    months_count = round(Decimal((FinishDate-StartDate).days/30.436875),1)
    spent_monthly = round((spent_with_cashback+spent_no_cashback)/months_count,2)

    if card_params[3] and cashback_total/months_count < Decimal(card_params[3]):
       cashback_monthly = round(cashback_total/months_count,2)
    else:
         cashback_monthly = Decimal(card_params[3])
         cashback_total = round(Decimal(card_params[3])*months_count,2)

    cashback_average_perc = round((cashback_total/spent_with_cashback)*100,2)

    if card_params[5]:
       costs_month_fixed = Decimal(card_params[5])
    else:
       costs_month_fixed = 0

 #    print (str(cashback_total) + " | " + str(cashback_high_mcc), flush=True)
    total_monthly_income = cashback_monthly-Decimal(AdditionalCosts)-costs_month_fixed


    return {'spent_with_cashback': spent_with_cashback, 'spent_no_cashback': spent_no_cashback, \
    'spent_monthly': spent_monthly, 'cashback_total': cashback_total, 'cashback_default': cashback_default, \
    'cashback_high_mcc': cashback_high_mcc, 'cashback_monthly': cashback_monthly, \
    'cashback_average_perc': cashback_average_perc, 'months_count': months_count, \
    'total_monthly_income': total_monthly_income}


@app.route('/', methods=['GET'])
def main():
    start_date = datetime.today() - timedelta(days=180)

    return render_template('index.html', card_names=card_names, \
    Start_Date = start_date.strftime('%Y-%m-%d'), Finish_Date = datetime.today().strftime('%Y-%m-%d'), \
    Additional_Costs = 0 )


@app.route('/', methods=['POST'])
def index_post():

    mcc_t = file_upload(request.files['MccFile'])
    CardName = request.form['CardName']
    StartDate = request.form['StartDate']
    FinishDate = request.form['FinishDate']
    AdditionalCosts = request.form['AdditionalCosts']

    card_params = all_card_params[card_names.index(CardName)]
    count_params = card_profit_calc(datetime.strptime(request.form['StartDate'],'%Y-%m-%d'), \
    datetime.strptime(request.form['FinishDate'],'%Y-%m-%d'), AdditionalCosts, card_params, mcc_t)

    return render_template('index.html', card_names=card_names, mcc_table = mcc_t, \
    Card_Name = CardName, Start_Date = StartDate, Finish_Date = FinishDate, Additional_Costs = AdditionalCosts, \
    Spent_With_Cashback = count_params['spent_with_cashback'], Spent_No_Cashback = count_params['spent_no_cashback'], \
    Spent_Monthly = count_params['spent_monthly'], Cashback_Total = count_params['cashback_total'], \
    Cashback_Default = count_params['cashback_default'], Cashback_High_Mcc = count_params['cashback_high_mcc'], \
    Cashback_Monthly = count_params['cashback_monthly'], Cashback_Average_Perc = count_params['cashback_average_perc'], \
    Months_Count = count_params['months_count'], Total_Monthly_Income = count_params['total_monthly_income'])


if __name__ == '__main__':
    app.run()
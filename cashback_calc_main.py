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
#print(number.quantize(Decimal("1.00")))

def csv_import(file_path):
#    results = []
    with open(file_path, newline='') as f:
         reader = list(csv.reader(f))
    return reader

all_card_params = csv_import('card_params.csv')
card_names_raw = [col[0] for col in all_card_params]
card_names = sorted(card_names_raw[1:])
card_names.insert(0, "Подобрать карты")


def file_upload(MccFile):
    if MccFile.filename == '':
       flash('No selected file')
    if MccFile:
       filename = datetime.today().strftime('%Y-%m-%d_%H-%M-%S') + "_" + secure_filename(MccFile.filename)
       MccFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

       file_path = app.config['UPLOAD_FOLDER'] + "/" + filename
       mcc_t = csv_import(file_path)

       #       for img in range(len(mcc_t)):
#           print (mcc_t[img], flush=True)
    return mcc_t


def cashback_calc (amount, round_rule, perc):
    perc = Decimal(perc)
    amount = Decimal(amount)

    if round_rule == 'До целых':
       cashback = Decimal(math.floor((amount/100)*perc))
    elif round_rule == 'До 50':
         cashback = math.floor((Decimal(math.floor(amount/50))/2)*perc*100)/100
    elif round_rule == 'До сотых':
         cashback = Decimal(math.floor(amount*perc))/100

    return cashback


def cashback_table_calc(card_params, mcc_t, choose_card = 0):

    cashback_table = []

    if choose_card == 1:
       for i in range(len(mcc_t)):
           table_line = []
           mcc = mcc_t[i][0]

           if re.match("(^[\d]{4}$)", mcc) and mcc_t[i][1]:
              amount = Decimal(mcc_t[i][1].replace("−", "").replace("-", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))

              table_line.append(mcc)
              table_line.append(str(amount))
              cashbacks_for_mcc = []
              for k in range(1, len(card_params)):

                  line = []
                  if mcc in card_params[k][7].split(", "):
                     line = [card_params[k][0]]
                     high_perc = Decimal(card_params[k][2].replace("%", "").replace(",", "."))
                     line.append(high_perc)
                     line.append(cashback_calc(amount, card_params[k][4], high_perc))
                  elif mcc in card_params[k][9].split(", "):
                     line = [card_params[k][0]]
                     high_perc2 = Decimal(card_params[k][8].replace("%", "").replace(",", "."))
                     line.append(high_perc2)
                     line.append(cashback_calc(amount, card_params[k][4], high_perc2))
                  elif mcc not in card_params[k][6].split(", "):
                     default_perc = Decimal(card_params[k][1].replace("%", "").replace(",", "."))
                     if default_perc != Decimal("0.00"):
                        line = [card_params[k][0]]
                        line.append(default_perc)
                        line.append(cashback_calc(amount, card_params[k][4], default_perc))

                  if line != []:
                     cashbacks_for_mcc.append(line)

              # find max cashback
              cashbacks_for_mcc_max = cashbacks_for_mcc[0]
              if len(cashbacks_for_mcc) > 1:
                 max_cashback = cashbacks_for_mcc[0][2]
                 for n in range(1, len(cashbacks_for_mcc)):
                     if cashbacks_for_mcc[n][2] > max_cashback:
                        cashbacks_for_mcc_max = cashbacks_for_mcc[n]
                        max_cashback = cashbacks_for_mcc[n][2]
                     elif cashbacks_for_mcc[n][2] == max_cashback:
                          cashbacks_for_mcc_max[0] = cashbacks_for_mcc_max[0] + ", " + cashbacks_for_mcc[n][0]


              table_line.append(str(cashbacks_for_mcc_max[2]))
              table_line.append(str(cashbacks_for_mcc_max[1]))
              table_line.append(cashbacks_for_mcc_max[0])

              cashback_table.append(table_line)

    else:
         no_mcc_list = card_params[6].split(", ")
         high_mcc_list = card_params[7].split(", ")
         high_mcc_list2 = card_params[9].split(", ")
         default_perc = Decimal(card_params[1].replace("%", "").replace(",", "."))

         if card_params[2]:
            high_perc = Decimal(card_params[2].replace("%", "").replace(",", "."))
         if card_params[8]:
            high_perc2 = Decimal(card_params[8].replace("%", "").replace(",", "."))

         for i in range(len(mcc_t)):
             table_line = []
             mcc = mcc_t[i][0]

             if re.match("(^[\d]{4}$)", mcc) and mcc_t[i][1]:
                amount = Decimal(mcc_t[i][1].replace("−", "").replace("-", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))
                table_line.append(mcc)
                table_line.append(str(amount))

                if mcc in high_mcc_list:
                   table_line.append(str(cashback_calc(amount, card_params[4], high_perc)))
                   table_line.append(str(high_perc))
                elif mcc in high_mcc_list2:
                     table_line.append(str(cashback_calc(amount, card_params[4], high_perc2)))
                     table_line.append(str(high_perc2))
                elif mcc in no_mcc_list:
                     table_line.append("0.00")
                     table_line.append("0.00")
                else:
                     table_line.append(str(cashback_calc(amount, card_params[4], default_perc)))
                     table_line.append(str(default_perc))

                cashback_table.append(table_line)

    return cashback_table


def card_profit_calc(StartDate, FinishDate, AdditionalCosts, card_params, cashback_table):

    cashback_total = Decimal(0)
    cashback_default = Decimal(0)
    cashback_high_mcc = Decimal(0)
    spent_with_cashback = Decimal(0)
    spent_no_cashback = Decimal(0)

    if card_params[2]:
       high_perc = card_params[2].replace("%", "").replace(",", ".")
    else:
       high_perc = ""

    if card_params[8]:
       high_perc2 = card_params[8].replace("%", "").replace(",", ".")
    else:
       high_perc2 = ""

    default_perc = card_params[1].replace("%", "").replace(",", ".")
    #print (high_perc, flush=True)

    for i in range(len(cashback_table)):
        amount = Decimal(cashback_table[i][1])
        cashback = Decimal(cashback_table[i][2])
        perc = cashback_table[i][3]

        cashback_total = cashback+Decimal(cashback_total)
        #print (high_perc, flush=True)
        if (high_perc or high_perc2) and (perc == high_perc or perc == high_perc2):
           cashback_high_mcc = cashback+cashback_high_mcc
           spent_with_cashback = amount+spent_with_cashback
        elif perc == "0.00":
             spent_no_cashback = amount+spent_no_cashback
#             print (spent_no_cashback, flush=True)
        elif perc == default_perc:
             cashback_default = cashback+cashback_default
             spent_with_cashback = amount+spent_with_cashback

    months_count = round(Decimal((FinishDate-StartDate).days/30.436875),1)
    spent_monthly = round((spent_with_cashback+spent_no_cashback)/months_count,2)
    cashback_monthly = round(cashback_total/months_count,2)

    if card_params[3]:
       cashback_limit_common = Decimal(card_params[3])
       if cashback_total/months_count > cashback_limit_common:
            cashback_monthly = cashback_limit_common
            cashback_total = round(cashback_limit_common*months_count,2)
            cashback_default = round((cashback_default/cashback_total)*cashback_limit_common*months_count,2)
            cashback_high_mcc = cashback_total-cashback_default

    cashback_average_perc = round((cashback_total/spent_with_cashback)*100,2)

    if card_params[5]:
       costs_month_fixed = Decimal(card_params[5])
    else:
       costs_month_fixed = 0

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


    if CardName == "Подобрать карты":
       card_params = all_card_params[card_names_raw.index(card_names[1])]
       cashback_table = cashback_table_calc(all_card_params, mcc_t, choose_card = 1)
    else:
         card_params = all_card_params[card_names_raw.index(CardName)]
         cashback_table = cashback_table_calc(card_params, mcc_t)
    #print (CardName + "|" + str(card_params), flush=True)


    count_params = card_profit_calc(datetime.strptime(request.form['StartDate'],'%Y-%m-%d'), \
    datetime.strptime(request.form['FinishDate'],'%Y-%m-%d'), AdditionalCosts, card_params, cashback_table)

    return render_template('index.html', card_names=card_names, Cashback_Table = cashback_table, \
    Card_Name = CardName, Start_Date = StartDate, Finish_Date = FinishDate, Additional_Costs = AdditionalCosts, \
    Spent_With_Cashback = count_params['spent_with_cashback'], Spent_No_Cashback = count_params['spent_no_cashback'], \
    Spent_Monthly = count_params['spent_monthly'], Cashback_Total = count_params['cashback_total'], \
    Cashback_Default = count_params['cashback_default'], Cashback_High_Mcc = count_params['cashback_high_mcc'], \
    Cashback_Monthly = count_params['cashback_monthly'], Cashback_Average_Perc = count_params['cashback_average_perc'], \
    Months_Count = count_params['months_count'], Total_Monthly_Income = count_params['total_monthly_income'])


@app.route('/cards', methods=['GET'])
def cards():

    return render_template('cards.html', All_Card_Params=all_card_params)


if __name__ == '__main__':
    app.run()
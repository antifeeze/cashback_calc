from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os, csv, math, re, decimal
from decimal import *
from datetime import datetime, timedelta

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
#getcontext().prec = 3
#getcontext().rounding = ROUND_DOWN
#print(number.quantize(Decimal("1.00")))

def csv_import(file_path):
#    results = []
    with open(file_path, newline='') as f:
         reader = list(csv.reader(f))
    return reader


all_card_params = csv_import('card_params.csv')
#all_card_params = [all_card_params[0], all_card_params[1], all_card_params[3], all_card_params[4], all_card_params[5]]


def file_upload(MccFile):
    ext = MccFile.filename.rsplit('.', 1)[1].lower()
    if MccFile.filename == '' or ext != "csv":
       return ["Wrong ext", ext]
    if MccFile:

       filename = datetime.today().strftime('%Y-%m-%d_%H-%M-%S') + "_" + secure_filename(MccFile.filename)
       #MccFile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
       file_path = app.config['UPLOAD_FOLDER'] + "/" + filename
       MccFile.save(file_path)

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
    wrong_file_elements = []

    if choose_card == 1:
       for i in range(len(mcc_t)):
           mcc = mcc_t[i][0].strip()
           amount = mcc_t[i][1].strip()

           if re.match("(^[\d]{4}$)", mcc) and re.match("(^[-+,.− \d\xa0]*\d+$)", amount):
              amount = Decimal(mcc_t[i][1].strip().replace("−", "").replace("-", "").replace("+", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))

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
              if len(cashbacks_for_mcc) >= 1:
                 cashbacks_for_mcc_max = cashbacks_for_mcc[0]
                 if len(cashbacks_for_mcc) > 1:
                    max_cashback = cashbacks_for_mcc[0][2]
                    for n in range(1, len(cashbacks_for_mcc)):
                        if cashbacks_for_mcc[n][2] > max_cashback:
                           cashbacks_for_mcc_max = cashbacks_for_mcc[n]
                           max_cashback = cashbacks_for_mcc[n][2]
                        elif cashbacks_for_mcc[n][2] == max_cashback:
                             cashbacks_for_mcc_max[0] = cashbacks_for_mcc_max[0] + ", " + cashbacks_for_mcc[n][0]

                 cashback_table.append([mcc, amount, str(cashbacks_for_mcc_max[2]), str(cashbacks_for_mcc_max[1]), cashbacks_for_mcc_max[0]])
              else:
                 cashback_table.append([mcc, amount, str(Decimal("0.00")), str(Decimal("0.00")), "Без кэшбэка"])
           else:
                if wrong_file_elements == []:
                   wrong_file_elements = ['wrong_file_elements']
                wrong_file_elements.append([mcc_t[i][0], mcc_t[i][1], i])
                #raise ValueError('Недопустимые символы в строке  таблицы покупок!')
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

    if wrong_file_elements != []:
       return wrong_file_elements
    else:
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

    #total_income = total_income-costs_month_fixed*months_count
    total_monthly_income = cashback_monthly-Decimal(AdditionalCosts)-costs_month_fixed

    return {'spent_with_cashback': spent_with_cashback, 'spent_no_cashback': spent_no_cashback, \
    'spent_monthly': spent_monthly, 'cashback_total': cashback_total, 'cashback_default': cashback_default, \
    'cashback_high_mcc': cashback_high_mcc, 'cashback_monthly': cashback_monthly, \
    'cashback_average_perc': cashback_average_perc, 'months_count': months_count, \
    'total_monthly_income': total_monthly_income}


def card_recom(cb_table, StartDate, FinishDate, all_card_params):

    months_count = round(Decimal((FinishDate-StartDate).days/30.436875),1)

    all_cards = []
    for card_names in [col[4] for col in cb_table]:
        for card_name in card_names.split(", "):
           if card_name not in all_cards:
              all_cards.append(card_name)

    recom_cards = []
    for card in all_cards:
        card_total_cashback = Decimal("0")
        for i in range(len(cb_table)):
            if card in cb_table[i][4].split(", "):
               card_total_cashback = card_total_cashback + Decimal(cb_table[i][2])

        recom_cards.append([card_total_cashback, card, round(card_total_cashback/months_count,2)])

    for n in range(len(cb_table)):
        if len(cb_table[n][4].split(", ")) > 1:

           spents = []
           for card in cb_table[n][4].split(", "):
               spents.append(recom_cards[[col[1] for col in recom_cards].index(card)][0])
           cb_table[n][4] = recom_cards[[col[0] for col in recom_cards].index(max(spents))][1]

    recom_cards = []
    for card in all_cards:
        card_total_cashback = Decimal("0")
        for i in range(len(cb_table)):
            if card in cb_table[i][4].split(", "):
               card_total_cashback = card_total_cashback + Decimal(cb_table[i][2])

        if all_card_params[[col[0] for col in all_card_params].index(card)][5]:
           total_income = card_total_cashback-Decimal(all_card_params[[col[0] for col in all_card_params].index(card)][5])*months_count
        else:
             total_income = card_total_cashback
        print(card_total_cashback)
        recom_cards.append([total_income, card, round(total_income/months_count,2)])

    recom_cards.sort(reverse=True)
    recom_cards.append([sum([col[0] for col in recom_cards]), "ИТОГО:", sum([col[2] for col in recom_cards])])
    #print(recom_cards)
    return recom_cards


@app.route('/', methods=['GET'])
def main():

    return render_template('index.html', \
    Start_Date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d'), \
    Finish_Date = datetime.today().strftime('%Y-%m-%d') )


@app.route('/', methods=['POST'])
def index_post():

    StartDate = request.form['StartDate']
    FinishDate = request.form['FinishDate']

    mcc_t = file_upload(request.files['MccFile'])
    if mcc_t[0] == "Wrong ext":
       return render_template('index.html', Wrong_Ext = mcc_t[1], \
       Start_Date = StartDate, Finish_Date = FinishDate)

    cashback_table = cashback_table_calc(all_card_params, mcc_t, choose_card = 1)

    if cashback_table[0] == "wrong_file_elements":
       return render_template('index.html', Wrong_Elements = cashback_table[1:], \
       Start_Date = StartDate, Finish_Date = FinishDate)

    recom_cards = card_recom(cashback_table, datetime.strptime(StartDate,'%Y-%m-%d'), datetime.strptime(FinishDate,'%Y-%m-%d'), all_card_params)

    return render_template('index.html', Cashback_Table = cashback_table, \
    Start_Date = StartDate, Finish_Date = FinishDate, Recom_Cards = recom_cards)


@app.route('/cards', methods=['GET'])
def cards():

    return render_template('cards.html', All_Card_Params=all_card_params)


if __name__ == '__main__':
    app.run()
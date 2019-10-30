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

       mcc_table = csv_import(file_path)
       #       for img in range(len(mcc_table)):
#           print (mcc_table[img], flush=True)
    return mcc_table


def check_mcc_table(mcc_table):
    wrong_file_elements = []
    for i in range(len(mcc_table)):
        if not (re.match("(^[\d]{4}$)", str(mcc_table[i][0]).strip()) and re.match("(^[-+,.− \d\xa0]*\d+$)", str(mcc_table[i][1]).strip())):
           if wrong_file_elements == []:
              wrong_file_elements = ['wrong_file_elements']
           wrong_file_elements.append([mcc_table[i][0], mcc_table[i][1], i])
    return wrong_file_elements


def cashback_calc (amount, round_rule, perc, amount_min_limit):
    perc = Decimal(perc)
    amount = Decimal(amount)
    amount_min_limit = Decimal(amount_min_limit)
    if amount < amount_min_limit:
       return 0
    else:
         if round_rule == 'До целых':
            cashback = Decimal(math.floor((amount/100)*perc))
         elif round_rule == 'До 50':
              cashback = math.floor((Decimal(math.floor(amount/50))/2)*perc*100)/100
         elif round_rule == 'До сотых':
              cashback = Decimal(math.floor(amount*perc))/100

         return cashback


def cashback_table_calc(card_params, mcc_table):

    cashback_table = []
    for i in range(len(mcc_table)):
        mcc = str(mcc_table[i][0]).strip()
        amount = Decimal(str(mcc_table[i][1]).strip().replace("−", "").replace("-", "").\
        replace("+", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))

        # find cashback for mcc from each card
        cashbacks_for_mcc = []
        for k in range(len(card_params)):

            line = []
            if mcc not in card_params[k][4].split(", "):
               for cat_line in card_params[k][5].splitlines():
                   perc = cat_line.split("% - ")[0]
                   cat_mcc_list = cat_line.split("% - ")[1].strip().split(", ")
                   if mcc in cat_mcc_list:
                      line = [card_params[k][0]]
                      line.append(perc)
                      line.append(cashback_calc(amount, card_params[k][3], perc, card_params[k][8]))
               if line == []:
                  line = [card_params[k][0]]
                  line.append(card_params[k][1].replace("%", "").replace(",", "."))
                  line.append(cashback_calc(amount, card_params[k][3], card_params[k][1].replace("%", "").replace(",", "."), card_params[k][8]))

            if line != []:
               cashbacks_for_mcc.append(line)

        # find max cashback
        if cashbacks_for_mcc == []:
           cashback_table.append([mcc, amount, "0.00", "0.00", "Без кэшбэка"])
        else:
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

    return cashback_table


def recom_cards_count(cashback_table, card_params, months_count):
    # get all card names from cashback_table
    all_cards = []
    for card_names in [col[4] for col in cashback_table]:
        for card_name in card_names.split(", "):
           if card_name != "Без кэшбэка":
              if card_name not in all_cards:
                 all_cards.append(card_name)
    # get recom cards list
    recom_cards = []
    for card in all_cards:
        card_total_income = Decimal("0")
        for i in range(len(cashback_table)):
            if card in cashback_table[i][4].split(", "):
               card_total_income = card_total_income + Decimal(cashback_table[i][2])

            issue_fee = Decimal(card_params[[col[0] for col in card_params].index(card)][6])
            monthly_fee = Decimal(card_params[[col[0] for col in card_params].index(card)][7])

            if card_params[[col[0] for col in card_params].index(card)][2] :
               monthly_cashback_limit = Decimal(card_params[[col[0] for col in card_params].index(card)][2])
               if card_total_income/months_count >  monthly_cashback_limit:
                  card_total_income = monthly_cashback_limit*months_count

            if card_params[[col[0] for col in card_params].index(card)][10] :
               turnover_to_free = Decimal(card_params[[col[0] for col in card_params].index(card)][10])
               if card_total_income/months_count > turnover_to_free:
                  monthly_fee = 0

            if card_params[[col[0] for col in card_params].index(card)][11] :
               notes = card_params[[col[0] for col in card_params].index(card)][11].split("\n")
            else:
                 notes = ""

        card_total_income = round(card_total_income - monthly_fee*months_count - issue_fee,2)

        recom_cards.append([card_total_income, card, round(card_total_income/months_count,2), notes])

    return recom_cards


def choose_one_card_per_purchase(cashback_table, recom_cards):
    for n in range(len(cashback_table)):
        if len(cashback_table[n][4].split(", ")) > 1:

           spents = []
           for card in cashback_table[n][4].split(", "):
               spents.append(recom_cards[[col[1] for col in recom_cards].index(card)][0])
           # modify cashback_table
           cashback_table[n][4] = recom_cards[[col[0] for col in recom_cards].index(max(spents))][1]
    return cashback_table


@app.route('/', methods=['GET'])
def main():

    return render_template('index.html', \
    Start_Date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d'), \
    Finish_Date = datetime.today().strftime('%Y-%m-%d') )


@app.route('/', methods=['POST'])
def index_post():

    StartDate = request.form['StartDate']
    FinishDate = request.form['FinishDate']
    months_count = round(Decimal((datetime.strptime(FinishDate, '%Y-%m-%d')-\
    datetime.strptime(StartDate, '%Y-%m-%d')).days/30.436875),1)

    # check input
    mcc_table = file_upload(request.files['MccFile'])
    if mcc_table[0] == "Wrong ext":
       return render_template('index.html', Wrong_Ext = mcc_table[1], \
       Start_Date = StartDate, Finish_Date = FinishDate)

    if len(check_mcc_table(mcc_table)) > 0:
       return render_template('index.html', Wrong_Elements = check_mcc_table(mcc_table), \
       Start_Date = StartDate, Finish_Date = FinishDate)

    card_params = all_card_params[1:]

    if not request.form.get('enable_pens_cards'):
       for n in list(card_params):
           if n[9] == "Да":
              card_params.remove(n)
       enable_pens_cards = 0
    else:
         enable_pens_cards = 1

    if not request.form.get('enable_credit_cards'):
       for n in list(card_params):
           if n[12] == "Кредитная":
              card_params.remove(n)
       enable_credit_cards = 0
    else:
         enable_credit_cards = 1

    if not request.form.get('enable_discount_cards'):
       for n in list(card_params):
           if n[13] in ["Скидка за баллы", "Мили"]:
              card_params.remove(n)
       enable_discount_cards = 0
    else:
         enable_discount_cards = 1
    #print(card_params)
    k = 1
    while k != 0:
          # count max cashback for each purchase
          cashback_table = cashback_table_calc(card_params, mcc_table)
          # count total income for each card for every purchase
          recom_cards = recom_cards_count(cashback_table, card_params, months_count)
          # choose card with max cashback per purchase and modify cashback_table
          cashback_table = choose_one_card_per_purchase(cashback_table, recom_cards)
          # count cashback for every purchase with the best card
          recom_cards = recom_cards_count(cashback_table, card_params, months_count)
          # remove cards with minus result
          k = 0
          for n in range(len(recom_cards)):
              if recom_cards[n][0] < 0:
                 card_params.remove(card_params[[col[0] for col in card_params].index(recom_cards[n][1])])
                 k += 1

    recom_cards.sort(reverse=True)
    recom_cards.append([sum([col[0] for col in recom_cards]), "ИТОГО:", sum([col[2] for col in recom_cards])])

    return render_template('index.html', Cashback_Table = cashback_table, \
    Enable_Pens_Cards = enable_pens_cards, Enable_Credit_Cards = enable_credit_cards, \
    Enable_Discount_Cards = enable_discount_cards, Start_Date = StartDate, \
    Finish_Date = FinishDate, Recom_Cards = recom_cards)


@app.route('/cards', methods=['GET'])
def cards():

    return render_template('cards.html', All_Card_Params=all_card_params)


if __name__ == '__main__':
    app.run()
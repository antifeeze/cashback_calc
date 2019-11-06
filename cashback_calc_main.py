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


#all_cards_params = csv_import('cards_params.csv')
#all_cards_params = [all_cards_params[0], all_cards_params[1], all_cards_params[3], all_cards_params[4], all_cards_params[5]]


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
       return Decimal(0)
    else:
         if round_rule == 'До целых':
            cashback = Decimal(math.floor((amount/100)*perc))
         elif round_rule == 'До 50':
              cashback = math.floor((Decimal(math.floor(amount/50))/2)*perc*100)/100
         elif round_rule == 'До сотых':
              cashback = Decimal(math.floor(amount*perc))/100

         return cashback


def get_cashbacks_for_mcc (cards_params, mcc, amount):

    cashbacks_for_mcc = []
    for k in range(len(cards_params)):

        line = []
        card_name = cards_params[k][0]
        round_rule = cards_params[k][2]
        mcc_excluded = cards_params[k][3]
        card_percents = cards_params[k][4]
        amount_min_limit = cards_params[k][7]

        if mcc not in mcc_excluded.split(", "):
           for cat_line in card_percents:
               perc = cat_line[0]
               mcc_list = cat_line[1]
               if mcc_list != "Остальные":
                  if mcc in mcc_list.split(", "):
                     cashback_amount = Decimal(cashback_calc(amount, round_rule, perc, amount_min_limit))
                     if cashback_amount > 0:
                        line = [card_name, perc, cashback_amount]

           if line == []:
              for cat_line in card_percents:
                  perc = cat_line[0]
                  mcc_list = cat_line[1]
                  if mcc_list == "Остальные":
                     cashback_amount = Decimal(cashback_calc(amount, round_rule, perc, amount_min_limit))
                     if cashback_amount > 0:
                        line = [card_name, perc, cashback_amount]

        if line != []:
           cashbacks_for_mcc.append(line)

    return cashbacks_for_mcc


# choose max cashback and find delta between previous max cashback
def choose_max_cashbacks_for_mcc(cashbacks_for_mcc):

    max_cashbacks_for_mcc = cashbacks_for_mcc[0]
    if len(cashbacks_for_mcc) > 1:
       max_cashbacks_for_mcc.append(cashbacks_for_mcc[0][2])
       max_local_cashback = cashbacks_for_mcc[0][2]
       for n in range(1, len(cashbacks_for_mcc)):
           if cashbacks_for_mcc[n][2] > max_local_cashback:
              max_cashbacks_for_mcc = cashbacks_for_mcc[n]
              max_cashbacks_for_mcc.append(cashbacks_for_mcc[n][2] - max_local_cashback)
              max_local_cashback = cashbacks_for_mcc[n][2]
           elif cashbacks_for_mcc[n][2] == max_local_cashback:
                max_cashbacks_for_mcc[0] = max_cashbacks_for_mcc[0] + ", " + cashbacks_for_mcc[n][0]
                max_cashbacks_for_mcc[3] = Decimal("0")
           elif cashbacks_for_mcc[n][2] < max_local_cashback:
                if max_cashbacks_for_mcc[3] > max_local_cashback - cashbacks_for_mcc[n][2]:
                   max_cashbacks_for_mcc[3] = max_local_cashback - cashbacks_for_mcc[n][2]
    else:
         max_cashbacks_for_mcc.append(cashbacks_for_mcc[0][2])

    return max_cashbacks_for_mcc


def create_cashback_table(cards_params, mcc_table, months_count, limit_recount_cards = []):

    cashback_table = []
    num = 0
    for i in range(len(mcc_table)):
        mcc = str(mcc_table[i][0]).strip()
        amount = Decimal(str(mcc_table[i][1]).strip().replace("−", "").replace("-", "").\
        replace("+", "").replace(" ", "").replace(",", ".").replace("\xa0", ""))

        # find cashback for this mcc from each card
        cashbacks_for_mcc = get_cashbacks_for_mcc(cards_params, mcc, amount)

        # find max cashback(s) for this mcc
        if cashbacks_for_mcc == []:
           cashback_table.append([num, mcc, amount, "0.00", "0.00", "Без кэшбэка", Decimal("0.00")])
        else:
             max_cashbacks_for_mcc = choose_max_cashbacks_for_mcc(cashbacks_for_mcc)
             cashback_table.append([num, mcc, amount, str(max_cashbacks_for_mcc[2]), \
             str(max_cashbacks_for_mcc[1]), max_cashbacks_for_mcc[0], max_cashbacks_for_mcc[3]])
        num += 1
    return cashback_table


def recom_cards_count(cashback_table, cards_params, months_count):
    # get all card names from cashback_table
    all_cards = []
    for card_names in [col[5] for col in cashback_table]:
        for card_name in card_names.split(", "):
           if card_name != "Без кэшбэка":
              if card_name not in all_cards:
                 all_cards.append(card_name)
    # get recom cards list
    recom_cards = []
    for card in all_cards:
        if cards_params[[col[0] for col in cards_params].index(card)][1]:
           cashback_limit = Decimal(cards_params[[col[0] for col in cards_params].index(card)][1])
        issue_fee = Decimal(cards_params[[col[0] for col in cards_params].index(card)][5])
        monthly_fee = Decimal(cards_params[[col[0] for col in cards_params].index(card)][6])
        card_total_income = Decimal("0")

        for i in range(len(cashback_table)):
            if card in cashback_table[i][5].split(", "):
               if (card_total_income + Decimal(cashback_table[i][3]))/months_count < cashback_limit:
                  card_total_income = card_total_income + Decimal(cashback_table[i][3])

        if cards_params[[col[0] for col in cards_params].index(card)][9]:
           turnover_to_free = Decimal(cards_params[[col[0] for col in cards_params].index(card)][9])
           if card_total_income/months_count > turnover_to_free:
              monthly_fee = 0

        if cards_params[[col[0] for col in cards_params].index(card)][10] :
           notes = cards_params[[col[0] for col in cards_params].index(card)][10].split("\n")
        else:
             notes = ""

        card_total_income = round(card_total_income - monthly_fee*months_count - issue_fee,2)

        recom_cards.append([card_total_income, card, round(card_total_income/months_count,2), notes])

    return recom_cards


def choose_one_card_per_purchase(cashback_table, recom_cards):
    for n in range(len(cashback_table)):
        if len(cashback_table[n][5].split(", ")) > 1:

           spents = []
           for card in cashback_table[n][5].split(", "):
               spents.append(recom_cards[[col[1] for col in recom_cards].index(card)][0])
           # modify cashback_table
           cashback_table[n][5] = recom_cards[[col[0] for col in recom_cards].index(max(spents))][1]
    return cashback_table


def modify_cashback_table(cashback_table, cards_params, months_count, limit_recount_cards):
    cashback_table_sorted = sorted(cashback_table, key=lambda x : float(x[6]),reverse=True)

    for card in limit_recount_cards:
        card_total_income = Decimal("0")
        cashback_limit = Decimal(cards_params[[col[0] for col in cards_params].index(card)][2])
        cards_paramss = list(cards_params)
        cards_paramss.remove(cards_params[[col[0] for col in cards_params].index(card)])
        for i in range(len(cashback_table_sorted)):
            if cashback_table_sorted[i][5] == card:
               card_total_income = card_total_income + Decimal(cashback_table_sorted[i][3])
               # choose new cards for mccs where limit exceeded
               if card_total_income/months_count > cashback_limit:
                  num = cashback_table_sorted[i][0]
                  mcc = cashback_table_sorted[i][1]
                  amount = cashback_table_sorted[i][2]
                  cashback_table_index = cashback_table[[col[0] for col in cashback_table].index(num)][0]

                  cashbacks_for_mcc = get_cashbacks_for_mcc(cards_paramss, mcc, amount)
                  # find max cashback(s) for this mcc

                  if cashbacks_for_mcc == []:
                     cashback_table[cashback_table_index][3] = "0.00"
                     cashback_table[cashback_table_index][4] = "0.00"
                     cashback_table[cashback_table_index][5] = "Без кэшбэка"
                     cashback_table[cashback_table_index][6] = Decimal("0.00")
                  else:
                       max_cashbacks_for_mcc = choose_max_cashbacks_for_mcc(cashbacks_for_mcc)
                       cashback_table[cashback_table_index][3] = str(max_cashbacks_for_mcc[2])
                       cashback_table[cashback_table_index][4] = str(max_cashbacks_for_mcc[1])
                       cashback_table[cashback_table_index][5] = str(max_cashbacks_for_mcc[0])
                       cashback_table[cashback_table_index][6] = Decimal(max_cashbacks_for_mcc[3])

    return cashback_table


def choose_card_percents(card_percents, monthly_turnover = 0):
    card_percents_mod = []
    percents_line = card_percents.splitlines()
    for a in percents_line:
         perc = a.split(" - ")[0].strip()
         mcc_list = a.split(" - ")[1].strip()
         if re.match("(^[\d.]+%$)", perc):
            percent = Decimal(perc.replace("%", ""))
            card_percents_mod.append([percent, mcc_list])
         else:
              max_percent = 0
              for n in perc.split(","):
                  percent = Decimal(n.strip().split("% ")[0])

                  turn_min_re = re.sub(r"^.*от ([\d.]+) р/мес.*$", r"\1", n.strip().split("% ")[1])
                  if re.match("(^[\d.]+$)", turn_min_re):
                     turn_min = turn_min_re
                  else:
                       turn_min = None

                  turn_max_re = re.sub(r"^.*до ([\d.]+) р/мес.*$", r"\1", n.strip().split("% ")[1])
                  if re.match("(^[\d.]+$)", turn_max_re):
                     turn_max = turn_max_re
                  else:
                       turn_max = None

                  if monthly_turnover != 0:
                     if turn_min is None and turn_max:
                        if monthly_turnover[1] < turn_max:
                           card_percents_mod.append([percent, mcc_list])
                     elif turn_min and turn_max:
                          if monthly_turnover[1] >= turn_min and monthly_turnover[1] < turn_max:
                             card_percents_mod.append([percent, mcc_list])
                     elif turn_min and turn_max is None:
                          if monthly_turnover[1] >= turn_min:
                             card_percents_mod.append([percent, mcc_list])
                  else:
                       if max(percent, max_percent) == percent:
                          max_percent = percent
                          card_percents_mod.append([percent, mcc_list])

    return card_percents_mod


@app.route('/', methods=['GET'])
def main():

    return render_template('index.html', \
    Start_Date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d'), \
    Finish_Date = datetime.today().strftime('%Y-%m-%d') )


@app.route('/', methods=['POST'])
def index_post():
    all_cards_params = csv_import('cards_params.csv')

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

    cards_params = all_cards_params[1:]

    if not request.form.get('enable_pens_cards'):
       for n in list(cards_params):
           if n[8] == "Да":
              cards_params.remove(n)
       enable_pens_cards = 0
    else:
         enable_pens_cards = 1

    if not request.form.get('enable_credit_cards'):
       for n in list(cards_params):
           if n[11] == "Кредитная":
              cards_params.remove(n)
       enable_credit_cards = 0
    else:
         enable_credit_cards = 1

    if not request.form.get('enable_discount_cards'):
       for n in list(cards_params):
           if n[12] in ["Скидка за баллы", "Мили"]:
              cards_params.remove(n)
       enable_discount_cards = 0
    else:
         enable_discount_cards = 1

    # choose cashback percent for each card
    for card_params in cards_params:
              card_percents = choose_card_percents(card_params[4])
              card_params[4] = card_percents

    k = 1
    limit_recount_cards = []
    while k != 0:
          # count max cashback for each purchase (could be several cards for each mcc)
          cashback_table = create_cashback_table(cards_params, mcc_table, months_count)
          # count total income for each card from short list and return recom_cards
          recom_cards = recom_cards_count(cashback_table, cards_params, months_count)
          # choose card with max cashback per mcc and modify cashback_table
          cashback_table = choose_one_card_per_purchase(cashback_table, recom_cards)
          # count cashback for every mcc with the best card
          recom_cards = recom_cards_count(cashback_table, cards_params, months_count)
          # recount in case of limit exceeding
          n = 0
          while n != 0:
                for n in range(len(recom_cards)):
                    if cards_params[[col[0] for col in cards_params].index(recom_cards[n][1])][2]:
                       if recom_cards[n][0]/months_count > Decimal(cards_params[[col[0] for col in cards_params].index(recom_cards[n][1])][2]):
                          if recom_cards[n][1] not in limit_recount_cards:
                             limit_recount_cards.append(recom_cards[n][1])
                if limit_recount_cards != []:
                   cashback_table = modify_cashback_table(cashback_table, cards_params, months_count, limit_recount_cards)
                   recom_cards = recom_cards_count(cashback_table, cards_params, months_count)
                   cashback_table = choose_one_card_per_purchase(cashback_table, recom_cards)
                   recom_cards = recom_cards_count(cashback_table, cards_params, months_count)
                   n += 1

          # remove cards with minus result
          k = 0
          for n in range(len(recom_cards)):
              if recom_cards[n][0] < 0:
                 cards_params.remove(cards_params[[col[0] for col in cards_params].index(recom_cards[n][1])])
                 k += 1


    recom_cards.sort(reverse=True)
    recom_cards.append([sum([col[0] for col in recom_cards]), "ИТОГО:", sum([col[2] for col in recom_cards])])

    return render_template('index.html', Cashback_Table = cashback_table, \
    Enable_Pens_Cards = enable_pens_cards, Enable_Credit_Cards = enable_credit_cards, \
    Enable_Discount_Cards = enable_discount_cards, Start_Date = StartDate, \
    Finish_Date = FinishDate, Recom_Cards = recom_cards)


@app.route('/cards', methods=['GET'])
def cards():
    all_cards_params = csv_import('cards_params.csv')
    return render_template('cards.html', All_Cards_Params=all_cards_params)


if __name__ == '__main__':
    app.run()
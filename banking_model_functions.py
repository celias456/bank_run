""" Banking Model Functions """
from statistics import mean
import random
import math
import numpy as np


def set_initial_deposits(model):
    """ Sets the total initial deposits """
    for bank in model.banks:
        model.total_initial_deposits += bank.initial_deposits


def allocate_budget(model):
    """
    Allocates a budget to each household
    The minimum budget is 350 and normalized to average 1000
    """
    household_budgets = []
    for household in model.households:
        household.budget = 350 + np.random.exponential(1000-350)
        household_budgets.append(household.budget)

    household_budgets_mean = round(mean(household_budgets), 3)

    for household in model.households:
        household.budget = round(
            (household.budget * (1000 / household_budgets_mean)) / 1000, 3)


def determine_savers(model):
    """ Determines which households are savers """
    savers = random.sample(model.households, model.num_savers)

    for saver in savers:
        saver.own_total_savings = 10


def month_reset(model):
    """ Resets variables at the beginning of the month """
    model.month_counter += 1
    model.max_lending_allowed = 0
    model.new_loan_supply = 0
    model.total_current_profit = 0
    model.total_expenditure = 0
    model.car_constraint_indicator = 0

    for household in model.households:
        household.potential_borrower = "No"
        household.loan_repaid = 0
        household.own_expenditure_this_month = 0
        household.seller = 0
        household.new_loan = "No"

    for bank in model.banks:
        bank.bad_debts = 0


def pay_households(model):
    """ Households receive thier income """
    for household in model.households:
        household.budget += household.budget


def collect_debts(model):
    """ 
    Banks collect regular repayments from borrowers 
    This does not run in the first month 
    """
    # If shock switched on then chosen per cent of borrowers default at chosen month
    if model.shock and model.month_counter == model.shock_month:
        borrowers = [
            household for household in model.households if household.own_outstanding_borrowing > 0]
        num_borrowers = len(borrowers)
        model.num_defaulters = round(
            (model.defaulters_percent / 100) * num_borrowers)
        defaulters = random.sample(borrowers, model.num_defaulters)
        defaulter_outstanding_borrowing = []
        for defaulter in defaulters:
            defaulter.defaulter = "Yes"
            defaulter.monthly_repayment = 0
            defaulter.borrowers_interest_payment = 0
            defaulter.capital_repayment = 0
            defaulter_outstanding_borrowing.append(
                defaulter.own_outstanding_borrowing)

        model.total_bad_debts = round(sum(defaulter_outstanding_borrowing))

        for defaulter in defaulters:
            defaulter.own_outstanding_borrowing = 0

    non_defaulters = [
        household for household in model.households if household.own_outstanding_borrowing > 0
        and household.defaulter == "No"]
    for non_defaulter in non_defaulters:
        non_defaulter.borrowers_interest_payment = round(
            non_defaulter.own_outstanding_borrowing * model.monthly_loan_rate, 3)
        non_defaulter.capital_repayment = round(
            non_defaulter.monthly_repayment - non_defaulter.borrowers_interest_payment, 3)
        non_defaulter.own_outstanding_borrowing = round(
            non_defaulter.own_outstanding_borrowing - non_defaulter.capital_repayment, 3)

    for household in model.households:
        household.own_expenditure_this_month = round(
            household.budget - household.monthly_repayment, 3)

    # For households that have paid off all of their debt
    non_borrowers = [
        household for household in model.households if household.own_outstanding_borrowing <= 0]
    for non_borrower in non_borrowers:
        non_borrower.own_outstanding_borrowing = 0
        non_borrower.own_loan = 0
        non_borrower.monthly_repayment = 0
        non_borrower.capital_repayment = 0
        non_borrower.borrowers_interest_payment = 0

    monthly_repayments = []
    capital_repayments = []
    borrowers_interest_payments = []
    for household in model.households:
        monthly_repayments.append(household.monthly_repayment)
        capital_repayments.append(household.capital_repayment)
        borrowers_interest_payments.append(
            household.borrowers_interest_payment)

    model.total_repayments = round(sum(monthly_repayments))
    model.total_capital_repayments = round(sum(capital_repayments))
    model.total_borrowers_interest_payments = round(
        sum(borrowers_interest_payments))


def pay_interest_to_savers(model):
    """
    Banks pay interest to savers and savers leave interest in accounts
    Does not run in first month - as paid in arrears
    """

    model.monthly_savers_rate = round(
        model.annual_savers_rate_percent / (12 * 100), 6)

    savers = [
        household for household in model.households if household.own_total_savings > 0]
    for saver in savers:
        saver.savers_interest_payment = round(
            saver.own_total_savings * model.monthly_savers_rate, 6)
        saver.own_total_savings = saver.own_total_savings + saver.savers_interest_payment

    savers_interest_payments = []
    for household in model.households:
        savers_interest_payments.append(household.savers_interest_payment)

    model.total_savers_interest_payments = round(sum(savers_interest_payments))


def collect_interest_on_liquid_assets(model):
    """
    Banks
    Does not run in first month - as paid in arrears
    """

    model.income_on_liquid_assets = round(
        model.total_banks_liquidity * model.monthly_savers_rate)


def make_deposits(model):
    """
    Does not run in first month as initial savings set
    spent_loans are generated by payments in the last round
    households only
    """

    for household in model.households:
        household.payment_history.append(household.spent_loan)

    sellers = [
        household for household in model.households if household.spent_loan > 0]
    for seller in sellers:
        seller.own_total_savings = seller.own_total_savings + seller.spent_loan
        seller.spent_loan = 0


def make_withdrawals(model):
    """
    Does not run in first month
    Adopters withdraw funds from bank
    """
    model.amount_withdrawn = 0
    runners = [
        household for household in model.households if household.adoption == "yes"
        and household.own_total_savings > 0]
    for runner in runners:
        model.amount_withdrawn += runner.own_total_savings
        runner.own_total_savings = 0
        runner.spent_loan = 0

    for household in model.households:
        household.saving_history.append(household.own_total_savings)

    # Funds must come from either bank's spare cash or bank's required liquidity
    # Funds come from spare cash reserve first, then required liquidity

    liquidity_buffer = model.banks_spare_cash - model.amount_withdrawn
    if liquidity_buffer >= 0:
        model.banks_spare_cash = liquidity_buffer
    else:
        model.banks_spare_cash = 0
        model.total_banks_required_liquidity += liquidity_buffer

    # Liquidity event check
    model.bank_liquid_assets = round(
        model.total_banks_required_liquidity + model.banks_spare_cash, 1)
    if model.bank_liquid_assets < 0:
        model.liquidity_event = 1
        model.liquidity_event_month = model.month_counter


def make_loans(model):
    """ Banks decide how much to lend """
    # Put aside funds to meet liquidity ratio
    own_total_savings = []
    for household in model.households:
        own_total_savings.append(household.own_total_savings)
    model.total_deposits_at_start_of_month = sum(own_total_savings)
    model.total_banks_required_liquidity = round(
        (model.total_deposits_at_start_of_month * model.target_reserve_ratio_percent) / 100)

    # Looks at how much lent
    # Takes repayments into account
    total_lending_at_start_of_month = []
    for household in model.households:
        total_lending_at_start_of_month.append(
            household.own_outstanding_borrowing)
    model.total_lending_at_start_of_month = round(
        sum(total_lending_at_start_of_month))

    # Calculate amount available for new loans
    total_capital = []
    for bank in model.banks:
        total_capital.append(bank.capital)
    model.total_capital = sum(total_capital)
    model.overall_balance_at_start_of_month = model.overall_balance_at_end_of_month

    # Includes spare cash by definition
    model.new_loan_supply = round(model.total_deposits_at_start_of_month -
                                  model.total_banks_required_liquidity -
                                  model.total_lending_at_start_of_month)

    model.new_loan_supply = max(0, model.new_loan_supply)

    # Check against capital adequacy ratio calculated at end of last month
    # - so can't be calculated for first month
    if model.month_counter == 1:
        model.new_loans_available = model.new_loan_supply
    elif model.month_counter > 1:
        if model.capital_adequacy_ratio_percent >= model.target_capital_adequacy_ratio_percent:
            model.new_loans_available = model.new_loan_supply
        else:
            model.car_constraint_indicator = 1
            model.max_rwa = (model.total_capital + model.total_retained_profit) / \
                (model.target_capital_adequacy_ratio_percent / 100)
            model.max_lending_allowed = model.max_rwa / \
                (model.risk_weight_loan_percent / 100)
            model.new_loans_available = round(
                model.max_lending_allowed - model.total_lending_at_start_of_month)

    # Check if new_loans_available is enough to make loans
    if model.new_loans_available < 0:
        model.new_loans_available = 0
        model.num_loans = 0

    # Loan size depends on type of loan
    if model.new_loans_available < model.loan_size:
        model.new_loans_available = 0
        model.num_loans = 0

    model.num_new_borrowers = "nk"

    # Rounding
    if model.new_loans_available > 0:
        model.num_loans = math.floor(
            model.new_loans_available / model.loan_size)
    if model.num_loans > 0:
        model.new_loans_available = model.num_loans * model.loan_size

    # No lending
    if model.num_loans == 0:
        model.num_new_borrowers = 0
        if model.month_loans_stop == 0:
            model.month_loans_stop = model.month_counter

    # Only one loan each
    # Monthly cost is set in setup and is same for all borrowers

    # Applies affordability test
    if model.affordability_test:
        household_potential_borrowers = [
            household for household in model.households if household.own_outstanding_borrowing == 0
            and (0.5 * household.budget) >= model.monthly_cost]
        for potential_borrower in household_potential_borrowers:
            potential_borrower.potential_borrower = "Yes"
    else:
        household_potential_borrowers = [
            household for household in model.households if household.own_outstanding_borrowing == 0]
        for potential_borrower in household_potential_borrowers:
            potential_borrower.potential_borrower = "Yes"

    model.potential_borrowers = len(household_potential_borrowers)

    if model.potential_borrowers == 0:
        model.num_new_borrowers = 0

    # Number of borrowers determined by supply of loan funds or eligibility
    if model.potential_borrowers != 0:
        if model.num_loans <= model.potential_borrowers:
            model.num_new_borrowers = model.num_loans
        else:
            model.num_new_borrowers = model.potential_borrowers

    # Households take loans
    new_loans = []
    household_potential_loan_takers = [
        household for household in model.households if household.own_outstanding_borrowing == 0
        and household.potential_borrower == "Yes"]
    household_loan_takers = random.sample(
        household_potential_loan_takers, model.num_new_borrowers)
    for household_loan_taker in household_loan_takers:
        # own_loan is the original loan that does not change
        household_loan_taker.own_loan = model.loan_size
        # starts off as the same as own_loan but is reduced by capital repayments
        household_loan_taker.own_outstanding_borrowing = household_loan_taker.own_loan
        # Monthly cost fixed in setup - same for all borrowers
        household_loan_taker.monthly_repayment = model.monthly_cost
        household_loan_taker.new_loan = "Yes"
        new_loans.append(household_loan_taker.own_loan)

    model.total_new_loans = sum(new_loans)

    # Banks spare cash is not cumulative
    model.banks_spare_cash = model.new_loan_supply - model.total_new_loans
    if model.banks_spare_cash < 0:
        model.loan_error = "Yes"


def spend_loans(model):
    """ Spend loans """
    # Identifies only those becoming borrowers this month; if used own_loan, would
    # include all borrowers
    new_loan_households = [
        household for household in model.households if household.new_loan == "Yes"]
    for new_loan_household in new_loan_households:
        seller = random.sample(model.households, 1)
        seller[0].spent_loan = new_loan_household.own_loan


def collect_data_at_end_of_month(model):
    """ Households borrow, banks lend
        Households save, banks have deposits
        Only one bank

        Bank's balance sheet
        assets = liquidity + lending + spare cash + current profit
        liabilities = deposits + capital + retained profit
    """
    model.total_current_profit = model.total_borrowers_interest_payments \
        + model.income_on_liquid_assets - model.total_savers_interest_payments \
        - model.total_bad_debts
    model.total_retained_profit += model.total_current_profit

    own_total_savings = []
    own_outstanding_borrowing = []
    own_expenditure_this_month = []
    for household in model.households:
        own_total_savings.append(household.own_total_savings)
        own_outstanding_borrowing.append(household.own_outstanding_borrowing)
        own_expenditure_this_month.append(household.own_expenditure_this_month)

    model.total_deposits_at_end_of_month = round(sum(own_total_savings), 0)
    model.total_lending_at_end_of_month = round(
        sum(own_outstanding_borrowing), 0)
    # Macro-level variable
    model.total_expenditure = round(sum(own_expenditure_this_month))

    total_capital_at_end_of_month = []
    for bank in model.banks:
        total_capital_at_end_of_month.append(bank.capital)
    model.total_capital_at_end_of_month = sum(total_capital_at_end_of_month)

    model.total_liabilities_at_end_of_month = model.total_deposits_at_end_of_month + \
        model.total_capital_at_end_of_month + model.total_retained_profit

    model.total_banks_liquidity = model.total_banks_required_liquidity + \
        model.banks_spare_cash + model.total_retained_profit + \
        model.total_capital_at_end_of_month

    model.total_assets_at_end_of_month = model.total_banks_liquidity + \
        model.total_lending_at_end_of_month

    model.overall_balance_at_end_of_month = round(
        model.total_assets_at_end_of_month - model.total_liabilities_at_end_of_month)

    # nb total_lending_at_start_of_month takes repayments into account
    model.check = model.total_lending_at_end_of_month - \
        (model.total_lending_at_start_of_month + model.total_new_loans)

    # Reserve Ratio
    model.reserve_ratio_percent = round(
        model.total_banks_liquidity / model.total_deposits_at_end_of_month * 100, 3)

    # Capital Adequacy Ratio
    # Risk weight allocated in set-up
    for bank in model.banks:
        bank.risk_weighted_exposure = model.total_lending_at_end_of_month * \
            model.risk_weight_loan_percent / 100

    risk_weighted_exposure = []
    for bank in model.banks:
        risk_weighted_exposure.append(bank.risk_weighted_exposure)
    model.total_risk_weighted_exposure = sum(risk_weighted_exposure)

    if model.total_risk_weighted_exposure > 0:
        model.capital_adequacy_ratio_percent = round(
            (model.total_capital
             + model.total_retained_profit)/model.total_risk_weighted_exposure * 100, 2)
        model.capital_adequacy_ratio_percent = max(
            model.capital_adequacy_ratio_percent, 0)
    else:
        model.capital_adequacy_ratio_percent = 0

    # Multipliers
    # Households hold no cash, so the money supply = deposits and the bank deposit
    # and money multipliers are the same
    model.bank_deposit_multiplier = model.total_deposits_at_end_of_month / \
        model.total_initial_deposits

    # Calculates statistics on borrowers and savers
    model.count_borrowers = 0
    amounts_borrowed = []
    model.count_savers = 0
    amounts_saved = []
    model.count_potential_borrowers = 0
    model.count_defaulters = 0
    model.average_amount_borrowed = 0
    model.average_amount_saved = 0

    for household in model.households:
        if household.own_outstanding_borrowing > 0:
            model.count_borrowers += 1
            amounts_borrowed.append(household.own_outstanding_borrowing)
        if household.own_total_savings >= 10:
            model.count_savers += 1
            amounts_saved.append(household.own_total_savings)
        if household.potential_borrower == "Yes":
            model.count_potential_borrowers += 1
        if household.defaulter == "Yes":
            model.count_defaulters += 1

    # Find average amount borrowed and saved
    if len(amounts_borrowed) > 0:
        model.average_amount_borrowed = mean(amounts_borrowed)
    if len(amounts_saved) > 0:
        model.average_amount_saved = mean(amounts_saved)

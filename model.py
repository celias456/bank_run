""" The Bank Run Model """
import random
from mesa import Agent, Model
from mesa.time import BaseScheduler
from mesa.space import ContinuousSpace
from mesa.datacollection import DataCollector
import banking_model_functions as bf
import threshold_model_functions as tf


class Households(Agent):
    """ A household """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

        self.budget = 0
        self.potential_borrower = "No"
        self.own_expenditure_this_month = 0
        self.own_total_savings = 0
        self.savers_interest_payment = 0
        self.spent_loan = 0
        self.own_outstanding_borrowing = 0
        self.new_loan = "No"
        self.own_loan = 0
        self.seller = 0
        self.monthly_repayment = 0
        self.borrowers_interest_payment = 0
        self.capital_repayment = 0
        self.defaulter = "No"
        self.loan_repaid = 0  # from payment i.e. in excess of monthly payments
        # These are to assist in debugging
        self.saving_history = []
        self.borrowing_history = []
        self.payment_history = []

        # From threshold model
        self.n_of_my_circle = 0
        self.status = 0
        self.my_threshold = 0
        self.n_of_adopting_friends = 0
        self.my_friends_adoption_percent = 0
        self.adoption = "no"
        self.time_adopted = "N/a"
        self.list_of_neighbors = []

    def move(self):
        """ Moves the household 1 cell in a random direction """
        # Steps fixed at 1

        # Get the person's current location
        position = list(self.pos)
        x_position = position[0]
        y_position = position[1]

        # Get a random integer between 0 and 8
        test = random.randint(1, 8)

        # If "test" is 1, decrease the "x" position by 1 unit
        # and increase the "y" position by 1 unit
        # If "test" is 2, increase the "y" position by 1 unit
        # If "test" is 3, increase the "x" position by 1 unit
        # and increase the "y" position by 1 unit
        # If "test" is 4, increase the "x" position by 1 unit
        # If "test" is 5, increase the "x" position by 1 unit
        # and decrease the "y" position by 1 unit
        # If "test" is 6, decrease the "y" position by 1 unit
        # If "test" is 7, decrease the "x" position by 1 unit
        # and decrease the "y" position by 1 unit
        # If "test" is 8, decrease the "x" position by 1 unit
        if test == 1:
            new_x = x_position - 1
            new_y = y_position + 1
        elif test == 2:
            new_x = x_position
            new_y = y_position + 1
        elif test == 3:
            new_x = x_position + 1
            new_y = y_position + 1
        elif test == 4:
            new_x = x_position + 1
            new_y = y_position
        elif test == 5:
            new_x = x_position + 1
            new_y = y_position - 1
        elif test == 6:
            new_x = x_position
            new_y = y_position - 1
        elif test == 7:
            new_x = x_position - 1
            new_y = y_position - 1
        else:
            new_x = x_position - 1
            new_y = y_position

        # Make sure agent's new position is not out of bounds
        if new_x < 0:
            new_x = x_position
        elif new_x > self.model.space_size-1:
            new_x = x_position

        if new_y < 0:
            new_y = y_position
        elif new_y > self.model.space_size-1:
            new_y = y_position

        self.model.space.remove_agent(self)
        self.model.space.place_agent(self, (new_x, new_y))

    def adopt(self):
        """ Household adopts """
        self.adoption = "yes"
        self.time_adopted = self.model.month_counter


class Banks(Agent):
    """ A bank """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

        self.initial_deposits = model.num_savers * 10
        self.deposits = self.initial_deposits
        self.banks_required_liquidity = round(
            self.deposits*model.target_reserve_ratio_percent/100)
        self.banks_actual_liquidity = 0
        self.lending = 0
        self.capital = model.equity_capital  # equity capital
        self.bad_debts = 0
        self.assets = 0
        self.liabilities = 0
        self.balance = 0
        self.risk_weighted_exposure = 0
        self.loan_supply = 0


class BankRunModel(Model):
    """ A bank run model """

    def __init__(self, num_households=1000, loan_type="mortgages", annual_loan_rate_percent=5,
                 num_savers=100, equity_capital=1000, target_reserve_ratio_percent=10, shock=0,
                 shock_month=12, defaulters_percent=1, annual_savers_rate_percent=2,
                 target_capital_adequacy_ratio_percent=10, affordability_test=1,
                 bank_run=1, social_shifting=1, social_shift_percent=5, social_reach=30,
                 innovators_percent=2.5, threshold="One-scattered", mean_threshold=50):
        super().__init__()
        self.num_households = num_households
        self.num_banks = 1
        self.loan_type = loan_type
        self.num_savers = num_savers
        self.equity_capital = equity_capital
        self.target_reserve_ratio_percent = target_reserve_ratio_percent
        self.shock = shock
        self.shock_month = shock_month
        self.defaulters_percent = defaulters_percent
        self.annual_savers_rate_percent = annual_savers_rate_percent
        self.target_capital_adequacy_ratio_percent = target_capital_adequacy_ratio_percent
        self.affordability_test = affordability_test
        self.num_defaulters = 0
        self.space_size = 0

        self.risk_weight_liquid_percent = 0
        self.risk_weight_mortgages_percent = 50
        self.risk_weight_consumer_loans_percent = 100

        self.total_initial_deposits = 0
        self.total_deposits_at_start_of_month = 0
        self.total_borrowing_at_start_of_month = 0
        self.total_lending_at_start_of_month = 0

        self.total_current_profit = 0
        self.total_borrowers_interest_payments = 0
        self.income_on_liquid_assets = 0
        self.total_savers_interest_payments = 0
        self.total_bad_debts = 0
        self.total_retained_profit = 0

        self.total_repayments = 0
        self.total_capital_repayments = 0
        self.total_capital = 0
        self.total_borrowers_interest_payments = 0

        self.total_banks_liquidity = 0
        self.total_banks_required_liquidity = 0
        self.banks_spare_cash = 0
        self.total_capital_at_end_of_month = 0
        self.total_assets_at_end_of_month = 0
        self.total_lending_at_end_of_month = 0
        self.total_deposits_at_end_of_month = 0
        self.total_liabilities_at_end_of_month = 0
        self.overall_balance_at_start_of_month = 0
        self.overall_balance_at_end_of_month = 0

        self.max_rwa = 0
        self.total_risk_weighted_exposure = 0

        self.annual_loan_rate_percent = annual_loan_rate_percent
        self.monthly_loan_rate = (annual_loan_rate_percent/12)/100
        self.monthly_savers_rate = 0
        self.new_loans_available = 0
        self.capital_adequacy_ratio_percent = 0
        self.num_loans = 0
        self.num_new_borrowers = ''
        self.month_loans_stop = 0
        self.potential_borrowers = 0
        self.total_new_loans = 0
        self.loan_error = "No"
        self.check = 0
        self.bank_deposit_multiplier = 0
        self.reserve_ratio_percent = 0

        self.month_counter = 1
        self.max_lending_allowed = 0
        self.new_loan_supply = 0
        self.total_expenditure = 0
        self.car_constraint_indicator = 0

        self.count_borrowers = 0
        self.count_savers = 0
        self.count_potential_borrowers = 0
        self.count_defaulters = 0
        self.average_amount_borrowed = 0
        self.average_amount_saved = 0

        # Bank run variables
        self.bank_run = bank_run
        self.amount_withdrawn = 0
        self.bank_liquid_assets = 0
        self.liquidity_event = 0
        self.liquidity_event_month = 0

        # This ensures density of agents is 1%
        if self.num_households == 1000:
            self.space_size = 316
        elif self.num_households == 5000:
            self.space_size = 706
        else:
            self.space_size = 1000

        # From threshold model
        self.count_of_innovators = 0
        self.households_listed_by_threshold = 0
        self.min_circle_size = 0
        self.av_circle_size = 0
        self.max_circle_size = 0
        self.n_with_no_circle = 0
        self.n_of_shifters = 0
        self.adopters_percent = 0
        self.adoption_percent_record = []
        self.min_my_threshold = 0
        self.median_my_threshold = 0
        self.mean_my_threshold = 0
        self.max_my_threshold = 0
        self.het = 0
        self.social_shifting = social_shifting
        self.social_shift_percent = social_shift_percent
        self.social_reach = social_reach
        self.innovators_percent = innovators_percent
        self.threshold = threshold
        self.mean_threshold = mean_threshold

        # Based on a total population of 1000
        self.n_of_innovators = int(self.innovators_percent*10)

        # Continuous space
        self.space = ContinuousSpace(self.space_size, self.space_size, True)

        # Types of loan
        if self.loan_type == "consumer loans":
            self.loan_term_months = 36
            self.loan_size = 5
            self.risk_weight_loan_percent = self.risk_weight_consumer_loans_percent

        if self.loan_type == "mortgages":
            self.loan_term_months = 300
            self.loan_size = 100
            self.risk_weight_loan_percent = self.risk_weight_mortgages_percent

        if self.monthly_loan_rate > 0:
            self.monthly_cost = round((self.loan_size*self.monthly_loan_rate) /
                                      (1 - ((1 + self.monthly_loan_rate)
                                            ** (-self.loan_term_months))), 3)
        else:
            self.monthly_cost = round(
                self.loan_size / self.loan_term_months, 3)

        self.schedule = BaseScheduler(self)
        self.running = True

        # Used to store agents
        self.households = []
        self.banks = []

        # Create households
        for count_households in range(self.num_households):
            household = Households(count_households, self)
            self.schedule.add(household)
            self.space.place_agent(household, (self.random.randrange(
                self.space_size), self.random.randrange(self.space_size)))
            self.households.append(household)

        # Create bank
        for count_banks in range(self.num_banks):
            bank = Banks(self.num_households + count_banks, self)
            self.schedule.add(bank)
            self.banks.append(bank)

        # Data collector
        self.datacollector = DataCollector(
            model_reporters={"Month": lambda a: a.month_counter,
                             "Cap_Ad":
                             lambda a: a.capital_adequacy_ratio_percent,
                             "Reserve": lambda a: a.reserve_ratio_percent,
                             "Capital": lambda a: a.total_capital_at_end_of_month / 1000,
                             "Deposits": lambda a: a.total_deposits_at_end_of_month / 1000,
                             "Profits": lambda a: a.total_retained_profit / 1000,
                             "Liabilities": lambda a: a.total_liabilities_at_end_of_month / 1000,
                             "Liquid": lambda a: a.total_banks_liquidity / 1000,
                             "Lending": lambda a: a.total_lending_at_end_of_month / 1000,
                             "Assets": lambda a: a.total_assets_at_end_of_month / 1000,
                             "Balance": lambda a: a.overall_balance_at_end_of_month / 1000,
                             "Multiplier": lambda a: a.bank_deposit_multiplier,
                             "Car_Constraint_Indicator": lambda a: a.car_constraint_indicator,
                             "Borrowers": lambda a: a.count_borrowers,
                             "Savers": lambda a: a.count_savers,
                             "Pot_Borrow": lambda a: a.count_potential_borrowers,
                             "Def": lambda a: a.count_defaulters,
                             "Loans": lambda a: a.loan_size,
                             "Borrowings": lambda a: a.average_amount_borrowed,
                             "Savings": lambda a: a.average_amount_saved,
                             "Borrowers_Interest_Payments":
                             lambda a: a.total_borrowers_interest_payments,
                             "Liquid_Asset_Income": lambda a: a.income_on_liquid_assets,
                             "Savers_Interest_Payments": lambda a: a.total_savers_interest_payments,
                             "Bad_Debts": lambda a: a.total_bad_debts,
                             "Current_Profit": lambda a: a.total_current_profit,
                             "Deposits_at_Start_of_Month":
                             lambda a: a.total_deposits_at_start_of_month,
                             "Required_Liquidity": lambda a: a.total_banks_required_liquidity,
                             "Lending_at_Start_of_Month":
                             lambda a: a.total_lending_at_start_of_month,
                             "New_Loans_Supply": lambda a: a.new_loan_supply,
                             "New_Loans_Made": lambda a: a.total_new_loans,
                             "Capital_Repayments": lambda a: a.total_capital_repayments,
                             "Total_Repayments": lambda a: a.total_repayments,
                             "Total_Expenditure": lambda a: a.total_expenditure,
                             "RWE": lambda a: a.total_risk_weighted_exposure,
                             "adopters_percent": lambda a: a.adopters_percent,
                             "Liquid_Assets": lambda a: a.bank_liquid_assets,
                             "liquidity_event": lambda a: a.liquidity_event,
                             "liquidity_event_month": lambda a: a.liquidity_event_month})

    def step(self):
        """ Advance the model by one step """
        if self.schedule.steps == 0:
            # Set initial deposits
            bf.set_initial_deposits(self)

            # Allocate budgets to households
            bf.allocate_budget(self)

            # Determine savers
            bf.determine_savers(self)

            if self.bank_run:  # Bank run is on
                # Create social circles
                tf.create_circles(self)

                # Initialize thresholds and determine innovators
                tf.initialize_thresholds_and_innovators(self)

            # Banks make loans
            bf.make_loans(self)

            # Borrowers spend loans
            bf.spend_loans(self)

            # Record the adoption rate
            tf.record_adoption_rate(self)

            # Collect data at end of month
            bf.collect_data_at_end_of_month(self)

        else:
            if self.liquidity_event == 0:
                # Monthly reset for necessary variables
                bf.month_reset(self)

                # Banks collect debts
                bf.collect_debts(self)

                if self.annual_savers_rate_percent > 0:
                    bf.pay_interest_to_savers(self)
                    bf.collect_interest_on_liquid_assets(self)

                # Households make deposits
                bf.make_deposits(self)

                # Banks make loans
                bf.make_loans(self)

                # Borrowers spend loans
                bf.spend_loans(self)

                if self.bank_run:
                    # Adopters make withdrawals
                    bf.make_withdrawals(self)

                # Move households and create new circles
                if self.social_shifting:
                    tf.shift(self)
                    tf.create_circles(self)

                # Spread adoption
                tf.spread(self)

                # Collect data at end of month
                bf.collect_data_at_end_of_month(self)

        # Collect data
        self.datacollector.collect(self)

        # Advance the model by one step
        self.schedule.step()

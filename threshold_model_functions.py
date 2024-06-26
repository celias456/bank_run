""" Threshold Model Functions """
from statistics import mean, median
import random
import numpy as np


def create_circles(model):
    """ Create social circles """
    circle_sizes = []
    for household in model.households:
        neighbors = household.model.space.get_neighbors(
            household.pos, household.model.social_reach, False)
        household.n_of_my_circle = len(neighbors)
        circle_sizes.append(household.n_of_my_circle)

    model.min_circle_size = 0
    model.av_circle_size = 0
    model.max_circle_size = 0
    if len(circle_sizes) != 0:
        model.min_circle_size = round(min(circle_sizes), 2)
        model.av_circle_size = round(mean(circle_sizes), 2)
        model.max_circle_size = round(max(circle_sizes))

    for household in model.households:
        if household.n_of_my_circle == 0:
            model.n_with_no_circle += 1


def initialize_thresholds_and_innovators(model):
    """ Determine thresholds and innovators """
    # Fixed threshold options - "Infection" models

    # Select innovators randomly
    if model.threshold == "One-scattered":
        # Set threshold
        for household in model.households:
            if household.n_of_my_circle > 0:
                household.my_threshold = 1
        # Select innovators
        innovators = random.sample(
            model.households, model.n_of_innovators)
        for innovator in innovators:
            innovator.adopt()
            innovator.status = "Innovator"

    if model.threshold == "One-clustered":
        # Set threshold
        for household in model.households:
            if household.n_of_my_circle > 0:
                household.my_threshold = 1
        # Select innovators to seed process
        innovators = random.sample(model.households, 1)
        for innovator in innovators:
            innovator.adopt()
            innovator.status = "Innovator"
        grow_network_of_innovators(model)

        # to ensure exactly required number of innovators
        if model.count_of_innovators > model.n_of_innovators:
            surplus = model.count_of_innovators - model.n_of_innovators
            potential_unadopters = [
                household for household in model.households if household.status == "Innovator"]
            unadopters = random.sample(potential_unadopters, surplus)
            for unadopter in unadopters:
                unadopter.status = 0
                unadopter.adoption = "no"

    # Heterogeneous Thresholds

    if model.threshold == "Heterogeneous-uniform":
        # Give everyone a social threshold from 1 to 100 distributed evenly
        for household in model.households:
            household.my_threshold = 1 + random.randint(0, 98)
        record_heterogeneous_thresholds(model)
        select_innovators(model)

    if model.threshold == "Heterogeneous-normal":
        # Give everyone a social threshold distributed normally with mean as set
        # by modeler and sd equal to the mean with adjustments to ensure values
        # lie between 0 and 100
        for household in model.households:
            household.my_threshold = round(
                1 + np.random.normal(model.mean_threshold, model.mean_threshold))
            if household.my_threshold < 0:
                household.my_threshold = model.mean_threshold
            if household.my_threshold > 100:
                household.my_threshold = model.mean_threshold
        record_heterogeneous_thresholds(model)
        select_innovators(model)


def grow_network_of_innovators(model):
    """
    Grows the network of innovators
    Increases radius above reach to increase likelihood of a single cluster
    rather than 2 or 3 smaller clusters
    """
    model.count_of_innovators = 0
    while model.count_of_innovators < model.n_of_innovators:
        adopters = [
            household for household in model.households if household.adoption == "yes"]
        for adopter in adopters:
            # Get neighbors
            neighbors = adopter.model.space.get_neighbors(
                adopter.pos, adopter.model.social_reach + 10, False)
            adopter.my_circle_non_adopters = [
                neighbor for neighbor in neighbors if neighbor.adoption == "no"]
            if len(adopter.my_circle_non_adopters) > 0:
                for nonadopter in adopter.my_circle_non_adopters:
                    nonadopter.adopt()
                    nonadopter.status = "Innovator"
            else:
                # no-one left in network, re-seed
                nonadopters = [
                    household for household in model.households if household.adoption == "no"]
                innovators = random.sample(nonadopters, 1)
                for innovator in innovators:
                    innovator.adopt()
                    innovator.status = "Innovator"
        adopters = [
            household for household in model.households if household.adoption == "yes"]
        model.count_of_innovators = len(adopters)


def record_heterogeneous_thresholds(model):
    """ Records heterogeneous thresholds """
    model.het = "yes"

    thresholds = []
    for household in model.households:
        thresholds.append(household.my_threshold)

    model.min_my_threshold = min(thresholds)
    model.median_my_threshold = median(thresholds)
    model.mean_my_threshold = mean(thresholds)
    model.max_my_threshold = max(thresholds)


def select_innovators(model):
    """ Selects innovators """
    model.households_listed_by_threshold = model.households.copy()
    model.households_listed_by_threshold.sort(key=lambda x: x.my_threshold)
    model.count_of_innovators = 0
    for _ in range(model.n_of_innovators):
        household = model.households_listed_by_threshold[model.count_of_innovators]
        household.adopt()
        household.status = "Innovator"
        model.count_of_innovators += 1


def record_adoption_rate(model):
    """ Record the adoption rate """
    adopters = [
        household for household in model.households if household.adoption == "yes"]
    model.adopters_percent = len(adopters) / 10
    model.adoption_percent_record.append(model.adopters_percent)


def shift(model):
    """ Social shifting """
    model.n_of_shifters = model.social_shift_percent * 10

    shifters = random.sample(
        model.households, model.n_of_shifters)

    for shifter in shifters:
        shifter.move()


def spread(model):
    """ Spread by influence or infection """

    if model.threshold == "One-scattered":
        spread_by_infection(model)
    elif model.threshold == "One-clustered":
        spread_by_infection(model)
    elif model.threshold == "Heterogeneous-uniform":
        spread_by_influence(model)
    else:
        spread_by_influence(model)

    # New adopters adopt
    new_households = [
        household for household in model.households if household.status == "new"]
    for new_household in new_households:
        new_household.adopt()
        new_household.status = 0

    # Record
    record_adoption_rate(model)


def spread_by_infection(model):
    """
    If any adopters in circle of non-adopters, non-adopters adopt
    Need to do this in two stages to avoid double-counting
    """
    non_adopters = [household for household in model.households if household.adoption ==
                    "no" and household.n_of_my_circle > 0]
    for non_adopter in non_adopters:
        neighbors = non_adopter.model.space.get_neighbors(
            non_adopter.pos, non_adopter.model.social_reach, False)
        adopting_neigbors = [
            neighbor for neighbor in neighbors if neighbor.adoption == "yes"]
        non_adopter.n_of_adopting_friends = len(adopting_neigbors)
        if non_adopter.n_of_adopting_friends >= 1:
            non_adopter.status = "new"


def spread_by_influence(model):
    """ Spread by influence """
    non_adopters_with_no_circle = [household for household in model.households
                                   if household.adoption == "no" and household.n_of_my_circle == 0]
    for non_adopter_with_no_circle in non_adopters_with_no_circle:
        non_adopter_with_no_circle.my_friends_adoption_percent = model.adopters_percent

    non_adopters_with_circle = [
        household for household in model.households
        if household.adoption == "no" and household.n_of_my_circle > 0]
    for non_adopter_with_circle in non_adopters_with_circle:
        neighbors = non_adopter_with_circle.model.space.get_neighbors(
            non_adopter_with_circle.pos, non_adopter_with_circle.model.social_reach, True)
        adopting_neighbors = [
            neighbor for neighbor in neighbors if neighbor.adoption == "yes"]
        non_adopter_with_circle.n_of_adopting_friends = len(adopting_neighbors)
        non_adopter_with_circle.my_friends_adoption_percent = \
            round((non_adopter_with_circle.n_of_adopting_friends /
                  non_adopter_with_circle.n_of_my_circle)*100, 1)

    non_adopters = [
        household for household in model.households if household.adoption == "no"]
    for non_adopter in non_adopters:
        if non_adopter.my_friends_adoption_percent >= non_adopter.my_threshold:
            non_adopter.status = "new"

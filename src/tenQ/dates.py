# Utility module containing date calculation methods for the 10Q format

from datetime import timedelta
import datetime


# Dates for final statements and their charges are defined by law. This
# module contains methods that makes it easy to calculate the dates correctly
# given a reference input date.

# Due date is defined as 1st of next month plus 3 months relative to the
# reference date. Here it is calculated by taking the first of the reference
# month and adding four months.
def get_due_date(reference_datetime):

    # Our resulting day should always be the 1st
    date = reference_datetime.replace(day=1).date()

    # always add 4 months so we get "first of next month + 3 months"
    add_months = 4

    # Add months, making sure to adjust year as neccessary
    if date.month+add_months <= 12:
        date = date.replace(month=date.month+add_months)
    else:
        date = date.replace(year=date.year+1, month=date.month+add_months-12)

    # Create the target date, but with the same time input as the reference
    # datetime.
    return timezone.make_aware(datetime.datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=reference_datetime.hour,
        minute=reference_datetime.minute,
        second=reference_datetime.second,
    ))


# Last payment date is the first workday on or after the 20th in the same month
# as the due date.
def get_last_payment_date_from_due_date(due_datetime):
    # Always the 20th of same month
    result = due_datetime.replace(day=20)

    # Cannot pay on saturday on sunday, so add the needed days to
    # get to monday, if neccessary.
    if result.weekday() in (5, 6):
        missing_days = 7-result.weekday()
        result += timedelta(days=missing_days)

    return result


def get_last_payment_date(reference_datetime):
    return get_last_payment_date_from_due_date(
        get_due_date(reference_datetime)
    )

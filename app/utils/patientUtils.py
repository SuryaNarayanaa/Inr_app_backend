from datetime import datetime, timedelta
import calendar
from collections import defaultdict



def get_medication_dates(start_date, prescription_list):
    start_date = datetime.strptime(start_date, "%d/%m/%Y")
    days_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    target_days = set(days_map[p["day"]] for p in prescription_list)

    medication_dates = []
    current_date = start_date
    end_date = datetime.now()

    while current_date <= end_date:
        if current_date.weekday() in target_days:
            medication_dates.append(current_date.strftime(str("%d-%m-%Y")))
        current_date += timedelta(days=1)

    print(medication_dates)

    return medication_dates

def should_take_dose_today(today, medication_dates_set):
    return today in medication_dates_set

def find_missed_doses(medication_dates_set, taken_dates_set):
    if taken_dates_set:
        return sorted(set(medication_dates_set) - set(taken_dates_set))
    else:
        return sorted(medication_dates_set)
    
def parse_report_date(date_input):
    if isinstance(date_input, datetime):
        return date_input
    
    if isinstance(date_input, str):
        formats = []
        if "T" in date_input:
            formats.append("%Y-%m-%dT%H:%M")
        else:
            formats.append("%d-%m-%Y")
        for fmt in formats:
            try:
                return datetime.strptime(date_input, fmt)
            except ValueError:
                continue
    raise ValueError(f"Date format not recognized: {date_input}")

def calculate_monthly_inr_average(inr_reports):

    monthly_sums = defaultdict(float)
    monthly_counts = defaultdict(int)

    if inr_reports == None: inr_reports = [{"date":"1900-01-01T00:00", "inr_value": 0}]

    for report in inr_reports:
        if isinstance(report["date"], datetime):
            date = report["date"]
        else:
            date =  parse_report_date(report["date"])
        month = calendar.month_abbr[date.month].upper()
        monthly_sums[month] += report["inr_value"]
        monthly_counts[month] += 1

    return {month: (monthly_sums[month] / monthly_counts[month]) for month in monthly_sums}
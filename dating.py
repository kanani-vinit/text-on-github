from datetime import datetime, timedelta

daysInWeek = 7
weeksInYears = 52

today = datetime.now()

sunday_this_week = today + timedelta(days=(6 - today.weekday()))

sunday_at_end = sunday_this_week - timedelta(days=daysInWeek)
sunday_at_start = sunday_this_week - timedelta(weeks=weeksInYears)



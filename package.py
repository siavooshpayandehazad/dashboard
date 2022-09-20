moodList = ["awful", "bad", "ok", "good", "great"]

weeks_of_the_year = [str(x) for x in range(1, 53)]

chart_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"]

days_of_the_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

HEADER = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'

temporary_data = {}

tracker_settings = {"workTracker": {"index": 1, "label": "work_hour", "accumulate": True},
                    "HR_Min": {"index": 2, "label": "HR_Min", "accumulate": False},
                    "HR_Max": {"index": 3, "label": "HR_Max", "accumulate": False},
                    "BP_Min": {"index": 4, "label": "BP_Min", "accumulate": False},
                    "BP_Max": {"index": 5, "label": "BP_Max", "accumulate": False},
                    "oxygenTracker": {"index": 6, "label": "BO", "accumulate": False},
                    "sleepTracker": {"index": 7, "label": "sleepTime", "accumulate": False},
                    "weightTracker": {"index": 8, "label": "weight", "accumulate": False},
                    "stepTracker": {"index": 9, "label": "steps", "accumulate": False},
                    "hydrationTracker": {"index": 10, "label": "hydration", "accumulate": False},
                    "runningTracker": {"index": 11, "label": "run", "accumulate": False},
                    "paceTracker": {"index": 12, "label": "pace", "accumulate": False},
                    "coffeeTracker": {"index": 13, "label": "coffee", "accumulate": False},
                    "moodTracker": {"index": 14, "label": "mood_name", "accumulate": False},
                    "log": {"index": 15, "label": "nan", "accumulate": False},
                    "activityTracker": {"index": 16, "label": "activity_tracker_name", "accumulate": False},
                    "activityPlanner": {"index": 17, "label": "activity_planner_name", "accumulate": False},
                    }
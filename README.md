## dashboard project

This is a simple personal dashboard project with todo lists, a simple scrum board, mood, activity and other trackers a journal which can display images as well, lists of books/movies etc. and a very simple notebook. The main idea here is that you are in control of your own data.

### How to run
clone the repo and move to the folder:

      git clone https://github.com/siavooshpayandehazad/dashboard.git
      cd dashboard

in your console run:

      virtualenv venv
      source venv/bin/activate
      pip install -r requirements.txt
      python3 dashboard.py

then go to the following tab for the main page:

     http://localhost:5000/

### How to Use
* CTL + l : locks the screen
* In journal page, you can navigate between pictures with left and right arrow keys and close the picture with scape.
* The password is set to "None" by default, you can change it in the settings page.
* Customize The Activity Tracker: you can add new activities or remove the ones you don't like `activityList` inside `package.py`.
* to enter data in the charts, click on the date on the chart, you will be prompted to enter your data.


### How to run tests
just run:
```
   cd tests
   pytest
```


### to add a new tracker
add your tracker in `tracker_settings` in `package.py`.
update the following functions: 
* `misc.py`: 
  * insert empty line in DB in `add_tracker_item_to_table`
  * tracker item in `generate_db_tables`
  * additional 'nan' in `clean_db`
* `charts.py`:
  * add new reader entry in `get_chart_data`
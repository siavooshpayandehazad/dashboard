dashboard project:
----------
This is a simple personal dashboard project with todo lists, mood and activity tracker a journal which can display images as well. The main idea here is that you are in control of your own data.

How to run:
----------
clone the repo and move to the folder:

      git clone https://SiavooshP@bitbucket.org/SiavooshP/dashboard.git
      cd dashboard

in your console run:

      virtualenv venv
      source venv/bin/activate
      pip install -r requirements.txt
      python3 dashboard.py

then go to the following tab for the main page:

     http://localhost:5000/home

The password is set to "None" by default, you can change it in the settings page.

Customize The Activity Tracker: you can add new activities or remove the ones you dont like `activityList` inside `package.py`.

To run tests run:
----------
```
   cd tests
   pytest
``

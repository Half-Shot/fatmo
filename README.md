# procatmo
Takes data from netatmo monitoring devices and puts it in a nice file oriented way (/proc style.)

### How to run:

* If run as a user, the files will be placed under /tmp/netatmo. Root will use /proc/netatmo.
* Run the application as your intended user and enter your login details
* The application will monitor the API, but you can close it.

* Run either in a screen or service file, the data will be automatically updated every 10 minutes and should continue to run until netatmo break something.

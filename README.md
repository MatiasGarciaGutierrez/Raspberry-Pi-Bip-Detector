# Raspberry Pi Bip Detector

The intent behind this project is to take multiple photos
when certain frequency is hear. 

Is implemented on a raspberry pi with an usb microphone and raspberry pi camera


## Dependencies

* Python3
* sounddevice 
* numpy
* picamera
* Pillow
* pynput

## Use

When you first launch this script it should be created the folder './samples' where it will be stored all the images with the follow format:

* ./samples
    * ./day-month-year
        * ./hour-minute-seconds
            * images


You can launch it with:

'''
python3 take_shots.py
'''

For exiting just press the esc key.



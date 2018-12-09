import sounddevice as sd
import numpy as np
import time
from pynput import keyboard
import picamera
from PIL import Image
import io
import datetime
import os


class FolderAdministrator():
    """This class is in charge of verify the existence and the creation of the folders use to store the images

        Attributes:
            samples_path (str): Correspond to the container folder of the images.
            now (datetime): The actual time set on the system.
    """

    def __init__(self, samples_path = "samples"):
        self.samples_path = samples_path
        self.now = None
        if not os.path.isdir(samples_path):
            os.mkdir(samples_path)

    def create_day_folder(self):
        """Create a folder for the day, if already exist does nothing.

            Args:
                    None

            Returns:
                    Relative path of the day folder.
        """
        self.update_date()
        date = str(self.now.day)+"-"+str(self.now.month)+"-"+str(self.now.year)
        path = self.samples_path+"/"+date
        if not os.path.isdir(path):
            os.mkdir(path)  
        return path

    def create_time_folder(self):
        """Creates a folder withe the corresponding time stamps

            Args:
                    None
            
            Returns:
                    Relative path to the time stamp container of the images.
        """
        self.update_date()
        date_path = self.create_day_folder()
        time = str(self.now.hour)+"-"+str(self.now.minute)+"-"+str(self.now.second)
        path = date_path+"/"+time
        os.mkdir(path)
        return path
    
    def update_date(self):
        """Updates the time with the system actual time.
        """
        self.now = datetime.datetime.now()


class PhotoAdministrator():
    """This class is in charge of taking burst of photos

        Attributes:
            camera (PiCamera): Raspberry pi camera instance from the PiCamera API.
            samples_path (str): Directory where the samples are storage
            folder_admin (FolderAdministrator): In charge of creating and organizing the time stamp folders.
    """
    def __init__(self, samples_path = "samples"):
        self.camera = self.create_camera()
        self.samples_path = samples_path
        self.folder_admin = FolderAdministrator()

    
    def create_camera(self, resolution = (640, 480), framerate = 80, rotation = 180):
        """Creates an instance of PiCamera and sets configurations. This configuration uses the video port (for photos uses still port), therefore, is    
           Susceptible to salt and pepper noise. The resolution was fix to 640x480, cause higher resolutions gets a maximun framerate of 49 fps (See PiCamera documentation "Chapter 6: Camera Hardware").
           With these resolution in theory we can get 90 FPS (less in practice).

            Args:
                    resolution (int tupple): Resolution of the images (width, height)
                    framerate (int): Number of images gets by the image sensor per second (Maximun 90 fps).
                    rotation (int): Rotation of the images (0 to 360). 
        """
        camera = picamera.PiCamera()
        camera.resolution = resolution
        camera.framerate = framerate
        camera.rotation = rotation
        time.sleep(1)
        return camera


    def photo_burst(self, number_of_shoots = 40, format = "jpeg"):
        """Creates a buffer of continuous photos and the saves it as a .npy file, the intention behind this implementation is save the image creation time.
           (When i measured the jpeg creation for 40 photos it was on the order of 2 seconds)

            Args:
                number_of_shoots (int): Number of shots to be taken, this number goes from 0 to framerate (at least in theory).
                format(str): Compression image file format.

            Returns:
                Nothing

        """
        outputs = [io.BytesIO() for i in range(number_of_shoots)]
        self.camera.capture_sequence(outputs, 'jpeg', use_video_port=True)    
        path = self.folder_admin.create_time_folder()
        self.save_output(path, outputs)
    

    def save_output(self, path, outputs):
        """Saves the outputs on a .npy file
        """
        np.save(path+"/"+"images", outputs)


    def create_jpg(self, folder_name):
        """Search for a folder and then creates the jpeg images saved in images.npy. 
           Creates all n the images store on the buffers inside the .npy, therefore, creates images with the name imagex.jpg with x between [1, n] 

            Args:
                folder_name(str): name of the folder relative to the samples path

            Returns:
                Nothing
        """
        images_data = np.load(self.samples_path+"/"+folder_name+"/"+"images"+".npy")
        count = 1
        for image_data in images_data:
            image_data.seek(0)
            byte_image = Image.open(image_data)
            filename = self.samples_path+"/"+folder_name+"/"+"image"+str(count)+".jpg"
            byte_image.save(filename, "JPEG")
            count = count + 1

    def create_all_jpg(self):
        """Creates all the jpg files if they are not already created.
        """
        for date_folder in os.listdir(self.samples_path):
            for time_folder in os.listdir(self.samples_path+"/"+date_folder):
                if(len(os.listdir(self.samples_path+"/"+date_folder+"/"+time_folder)) == 1): #Condition if in the folder are more than 1 files.
                    self.create_jpg(date_folder+"/"+time_folder)



class FrequencyDetector():
    """This class manages the frequency detection. Takes samples of sounds in short periods of time and then calculates the fourier transform of it
       Once it has the fourier transforms look for the highest value of it (i.e the principal harmonic) and compare it with the search frequency.

       Attributes:
            duration (float): Second of recording in each iteration. Actual best value i try is 0.05 second (didn't recognize all the bips)
            sample_rate (int): Number of samples take by the microphone in 1 second, also gives the maximun frequency to be detected (nyquist theorem).
            device (int): Number of the device to be used (in computers is default by cero, on raspberry pi usb microphone is 2)
            channels (int): Number of channels of the recording (mono 1 or stereo 2). We use mono.
            photo_administrator (PhotoAdministrator): Instance of PhotoAdministrator class. Is used as a manager for taking the burst of images.

    """

    def __init__(self, duration, sample_rate, device, channels = 1):
        self.duration = duration
        self.sample_rate = sample_rate
        self.device = device
        self.channels = channels
        self.photo_administrator = PhotoAdministrator()

    def detect(self, frequency, threshold = 50):
        """Creates recording of duration second and the calculates the fourier transform -> if the difference between the wanted frequency es lower than threshold
           then, take a burst of images with method photo_bust of PhotoAdministrator. Also the while loop is linked with the global variable break_program (change by the event of pressing esc key).
           When this loop is break creates all the jpg files from the npy file that were not created before. 

            Args:
                frequency (float): Frequency to be detected
                threshold (float): Maximum difference between frequencies to make a match

            Returns:
                Nothing      
        """
        while (not break_program):
            my_recording = sd.rec(int(self.duration * self.sample_rate), samplerate=self.sample_rate, channels=self.channels, device=self.device)
            time.sleep(1.1*self.duration)
            fourier = np.fft.fft(my_recording.ravel())
            half_size = int(fourier.size/2)
            f_max_index = np.argmax(abs(fourier[:half_size]))
            freqs = np.fft.fftfreq(len(fourier))
            f_detected = freqs[f_max_index]*self.sample_rate
            if (abs(f_detected - frequency) < threshold):
                print(f_detected)
                print("detectado")
                self.photo_administrator.photo_burst()      
        self.photo_administrator.create_all_jpg()      




def on_press(key):
    """Function made for waiting the event of pressing esc key
    """
    global break_program
    if key == keyboard.Key.esc:
        print ('end pressed')
        break_program = True
        return False


break_program = False
if __name__ == "__main__":
    with keyboard.Listener(on_press=on_press) as listener:
        frequency_detector = FrequencyDetector(0.05, 44100, 2)
        while (not break_program):
            frequency_detector.detect(1060)
        listener.join()
    










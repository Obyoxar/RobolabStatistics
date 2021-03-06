import cv2
import robolib.modelmanager.downloader as downloader
from robolib.networks.erianet import Erianet
from robolib.networks.configurations import VGG19ish
from robolib.networks.common import contrastive_loss_manual
import time
import threading
import os
import matplotlib.pyplot as plt
from tensorflow.python.client import device_lib
from robolib.networks.predict_result import PredictResult
import robolib.datamanager.datadir as datadir
# https://www.openu.ac.il/home/hassner/data/lfwa/


class PersonData:
    def __init__(self, name):
        self.name = name
        self.timeout_in = 1
        self.timeout_out = 0
        self.probability = 0

    # Returns False if person was not even recognised 3 frames in a row
    def recognised(self, recognised):
        if recognised:
            if self.timeout_in < 4:
                self.timeout_in += 1
                if self.timeout_in == 3:
                    self.timeout_out = 8
            else:
                self.timeout_out = 8
        else:
            if self.timeout_in < 3:
                return False
            else:
                self.timeout_out -= 1
        return True


class Mainloop(threading.Thread):
    def __init__(self, data_folder, log_folder, face_cascades, model_path, config, input_image_size=(96, 128),
                 input_to_output_stride=2, insets=(0, 0, 0, 0), for_train=False, log=False, hidden=False, timeout_in=3,
                 timeout_out=8, video_capture=0):
        threading.Thread.__init__(self)
        self.interrupted = True
        self.vcap = video_capture
        self.data_folder = datadir.get_intermediate_dir(data_folder)
        self.log_folder = log_folder
        self.timeout_in = timeout_in
        self.timeout_out = timeout_out
        self.face_cascades = face_cascades
        self.log = log
        self.hidden = hidden
        self.person_list = []
        self.timeline = dict()
        self.model_path = datadir.get_model_dir(model_path)
        self.config = config
        self.input_image_size = input_image_size
        self.input_to_output_stride = input_to_output_stride
        self.insets = insets
        self.for_train = for_train
        self.net = None
        self.to_hide = False
        self.to_show = False

        if not os.path.exists(self.data_folder):
            raise FileNotFoundError(self.data_folder)
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(self.model_path)

    def interrupt(self):
        self.interrupted = True

    def is_interrupted(self):
        return self.interrupted

    def hide(self):
        """
        Hides all windows
        """
        if not self.hidden:
            self.to_hide = True
        if self.to_show:
            self.to_show = False

    def show(self):
        """
        Shows all windows
        """
        if self.hidden:
            self.to_show = True
        if self.to_hide:
            self.to_hide = False

    def __get_resized_faces(self, img_to_resize):
        gray = cv2.cvtColor(img_to_resize, cv2.COLOR_BGR2GRAY)
        faces, rejectlevels, levelleights = self.face_cascades.detectMultiScale3(gray, 1.3, 5, 0, (60, 60), (480, 480), True)
        res_faces = []
        for face in faces:
            x, y, w, h = face
            if y - 0.22 * h < 0 or y + h * 1.11 > img_to_resize.shape[0]:
                continue
            face = gray[int(y - 0.22 * h):int(y + h * 1.11), x:x + w]
            res_face = cv2.resize(face, dst=None, dsize=(96, 128), interpolation=cv2.INTER_LINEAR)
            res_faces.append(res_face)
        return res_faces

    def __show_faces(self, faces, names):
        for person in self.person_list:
            for name in names:
                if person.name == name and person.timeout_in >= self.timeout_in:
                    cv2.putText(faces[names.index(name)], str(person.probability), (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 255, 0), 2)
                    cv2.imshow(name, faces[names.index(name)])
                    cv2.waitKey(30)

    def __recognise_faces(self, faces):
        names = []
        ts = time.time()
        for face in reversed(faces):
            predicted_person = self.net.predict(face, self.data_folder)
            #print(predicted_person)
            for person in self.person_list:
                if person.name == PredictResult.name(predicted_person[0]):
                    person.probability = PredictResult.difference(predicted_person[0])
            exists = False
            for name in names:
                if name == PredictResult.name(predicted_person[0]):
                    faces.remove(face)
                    exists = True
            if not exists:
                names.insert(0, PredictResult.name(predicted_person[0]))
            #print(predicted_person)
            #print("Correct: {0} - Incorrect:{0}".format(contrastive_loss_manual(True, predicted_person[0][2]),
                                                        #contrastive_loss_manual(False, predicted_person[0][2])))
            #for name in predicted_person:
                #if PredictResult.name(name) not in timeline:
                    #print(name[0])
                    #timeline[PredictResult.name(name)] = [[ts], [PredictResult.difference(name())]]
                #else:
                    #timeline[PredictResult.name(name)][0].append(ts)
                    #timeline[PredictResult.name(name).append(name[1])
        return names

    def __set_timeouts(self, names):
        # checking for already recognised people
        for person in reversed(self.person_list):
            exists = False
            for name in names:
                if name == person.name:
                    exists = True
            if not person.recognised(exists):
                self.person_list.remove(person)
        # checking for newly recognised people
        for name in names:
            exists = False
            for person in self.person_list:
                if name == person.name:
                    exists = True
            if not exists:
                self.person_list.append(PersonData(name))
        #for person in self.person_list:
            #print("Person: " + person.name + ", Timeout in: " + str(person.timeout_in) + ", Timeout out: " + str(person.timeout_out))

    def __create_or_destroy_windows(self):
        for person in reversed(self.person_list):
            if person.timeout_in == self.timeout_in and person.timeout_out == self.timeout_out:
                if not self.hidden:
                    cv2.namedWindow(person.name)
            elif person.timeout_in >= self.timeout_in and person.timeout_out == 0:
                if not self.hidden:
                    cv2.destroyWindow(person.name)
                self.person_list.remove(person)

    def __log(self, names, faces):
        if not os.path.isdir(self.log_folder):
            os.makedirs(self.log_folder)
        if not os.path.isdir(self.log_folder + '/pictures'):
            os.makedirs(self.log_folder + '/pictures')
        file = open(self.log_folder + '/log.txt', 'a')
        for person in self.person_list:
            if person.timeout_in == self.timeout_in and person.timeout_out == self.timeout_out:
                file.write(time.strftime('%Y-%b-%d;%H:%M:%S;') + person.name + '\n')
                face = faces[names.index(person.name)]
                cv2.imwrite(self.log_folder + '/pictures/' + time.strftime('%Y-%b-%d-%H-%M-%S-') + person.name + ".pgm", face)
        file.close()

    def run(self):
        self.interrupted = False
        self.person_list = []
        cap = cv2.VideoCapture(self.vcap)
        if self.net is None:
            self.net = Erianet(self.model_path, input_image_size=self.input_image_size, config=self.config,
                               input_to_output_stride=self.input_to_output_stride, insets=self.insets,
                               for_train=self.for_train)
        cv2.namedWindow('img')
        while not self.interrupted:
            if self.to_show:
                self.to_show = False
                for person in self.person_list:
                    if person.timeout_in > 2:
                        cv2.namedWindow(person.name)
                self.hidden = False
            ret, img = cap.read()
            resized_faces = self.__get_resized_faces(img)
            recognised_names = self.__recognise_faces(resized_faces)
            self.__set_timeouts(recognised_names)
            if self.log:
                self.__log(recognised_names, resized_faces)
            self.__create_or_destroy_windows()
            if not self.hidden:
                cv2.imshow('img', img)
                self.__show_faces(resized_faces, recognised_names)
                k = cv2.waitKey(30) & 0xff
                if k == 27:
                    self.interrupt()
            if self.to_hide:
                self.to_hide = False
                cv2.destroyAllWindows()
                self.hidden = True
        cap.release()
        cv2.destroyAllWindows()
        """legend = []
        for key, value in self.timeline.items():
            plt.plot(value[0], value[1])
            legend.append(key)

        plt.legend(legend, loc='upper left')
        plt.show()"""


def main():
    MODEL_FILE = downloader.get_model(downloader.HAARCASCADE_FRONTALFACE_ALT, False)
    main_face_cascades = cv2.CascadeClassifier(MODEL_FILE)
    main = Mainloop('3BHIFinterm', 'log', main_face_cascades, 'bigset_4400_1526739422044.model', VGG19ish,
                    input_image_size=(96, 128), log=True)
    print("Commands available: start, hide, show, stop")
    main_input = ''
    while main_input != 'stop':
        main_input = input("Mainloop: ")
        if main_input == 'start':
            if main.is_interrupted():
                main.start()
        elif main_input == 'stop':
            if not main.is_interrupted():
                main.interrupt()
        elif main_input == 'hide':
            main.hide()
        elif main_input == 'show':
            main.show()


if __name__ == '__main__':
    main()

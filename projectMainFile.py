import os, config, cv2, numpy as np
from tkinter import Tk, font, Button, filedialog, Label
from PIL import ImageTk, Image


# ------------------------------------------------------------------------- #
# Klasa stworzona do zliczania aut, jeśli samochód przekroczy pewien obszar
class Box:
    def __init__(self, start_point, width_height):
        self.start_point = start_point
        self.end_point = (start_point[0] + width_height[0], start_point[1] + width_height[1])
        self.counter = 0
        self.frame_countdown = 0

    def overlap(self, start_point, end_point):
        if self.start_point[0] >= end_point[0] or self.end_point[0] <= start_point[0] or \
                self.start_point[1] >= end_point[1] or self.end_point[1] <= start_point[1]:
            return False
        else:
            return True


# ------------------------------------------------------------------------- #
# Tworzenie małych obszarów na pasach drogi w wideo, aby można było policzyc
# ile aut jechało danym pasem, a następnie zliczyć sumę wszystkich samochodów
def box_creator(boxes, filename):
    if filename == 'highway.mp4' or filename == 'highway2.mp4':
        boxes.append(Box((200, 500), (180, 10)))
        boxes.append(Box((440, 500), (100, 10)))
        boxes.append(Box((700, 500), (120, 10)))
        boxes.append(Box((900, 500), (200, 10)))
    elif filename == 'forest.mp4' or filename == 'forest2.mp4':
        boxes.append(Box((380, 400), (200, 10)))
        boxes.append(Box((680, 400), (130, 10)))
        boxes.append(Box((900, 400), (250, 10)))


# ------------------------------------------------------------------------- #
# Funkcja wykrywajaca samochody
def capture_cars_from_source():
    # ------------------------------------------------------------------------- #
    # Otwieranie plikow

    file = filedialog.askopenfilename(initialdir=os.getcwd(), title="Wybierz film", filetypes=[("mp4 files", '.mp4')])
    open(file, 'r')
    print("File '" + os.path.basename(file) + "' has been opened.")

    # ------------------------------------------------------------------------- #
    # Inicjalizacja linii, poniżej której wykrywane są pojazdy w określonych plikach wideo
    if os.path.basename(file) == 'highway.mp4' or os.path.basename(file) == 'highway2.mp4':
        line_x = 0
        line_y = 350
    elif os.path.basename(file) == 'forest.mp4' or os.path.basename(file) == 'forest2.mp4':
        line_x = 0
        line_y = 200

    cap = cv2.VideoCapture(file)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    text = ""
    boxes = []
    frames = []
    thresh_frames = []
    eroded_frames = []

    kernel = np.ones((7, 7), np.uint8)
    wait_key = 5
    amount = 0
    i = 0

    # ------------------------------------------------------------------------- #
    # Petla glowna
    while True:
        if i >= frame_count:
            break

        flag, frame = cap.read()
        frames.append(frame)
        if flag:
            # ------------------------------------------------------------------------- #
            # Stworzenie pojemników na pasach jezdni (dokladniejszy opis w linii 24)
            if i == 0:
                box_creator(boxes, os.path.basename(file))
            if i != 0:
                height, width = frames[0].shape[:2]
                # ------------------------------------------------------------------------- #
                # Obliczanie różnicy pomiędzy dwoma następującymi po sobie klatkami, aby
                # wyodrębnić obiekty, które się poruszały
                gray_a = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
                gray_b = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
                diff_image = cv2.absdiff(gray_a, gray_b)

                # ------------------------------------------------------------------------- #
                # Progowanie różnicy obrazów
                ret, thresh = cv2.threshold(diff_image, 30, 255, cv2.THRESH_BINARY)
                thresh_frames.append(thresh)
                # ------------------------------------------------------------------------- #
                # Zamknięcie wykrytych obiektów
                closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                # ------------------------------------------------------------------------- #
                # Usunięcie szumów
                closing = cv2.medianBlur(closing, 5)
                # ------------------------------------------------------------------------- #
                # Ponowne zamknięcie obiektów po zredukowaniu szumu
                closing = cv2.morphologyEx(
                    closing, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    )
                # ------------------------------------------------------------------------- #
                # Erozja mająca na celu dokładniejsze wyodrębnienie poruszających się obiektów
                eroded = cv2.morphologyEx(closing, cv2.MORPH_ERODE, kernel)
                eroded_frames.append(eroded)

                # ------------------------------------------------------------------------- #
                # Wykrywanie konturów
                contours, hierarchy = cv2.findContours(eroded.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

                for j in range(len(contours)):
                    # ------------------------------------------------------------------------- #
                    # Odnajdywanie nadrzędnego konturu - usunięcie efektu 'ramki w ramce'
                    if hierarchy[0, j, 3] == -1:
                        x, y, w, h = cv2.boundingRect(contours[j])
                        # ------------------------------------------------------------------------- #
                        # Zaznaczenie wszystkich poruszających się obiektów poniżej linii, które mają odpowiedni rozmiar
                        if (x >= line_x) & (y >= line_y) & (
                                cv2.contourArea(contours[j]) >= config.sizeOfDetectedObject):
                            cv2.drawContours(frames[i], contours[j], -1, config.frameColor, 4)
                            cv2.rectangle(frames[i - 1], (x, y), (x + w, y + h), config.magentaColor, 2)
                            # ------------------------------------------------------------------------- #
                            # Zliczanie przemieszczających się pojazdów:
                            text = "Zliczone pojazdy:"
                            for box in boxes:
                                box.frame_countdown -= 1
                                if box.overlap((x, y), (x + w, y + h)):
                                    if box.frame_countdown <= 0:
                                        box.counter += 1
                                        amount += 1
                                    box.frame_countdown = 20
                            text += str(amount)

                # ------------------------------------------------------------------------- #
                # *Opcjonalnie* - wyświetlanie pojemników na pasach jezdni, wystarczy odkomentować poniższe dwie linie
                for box in boxes:
                    cv2.rectangle(frame, box.start_point, box.end_point, config.orangeColor, 2)

                # ------------------------------------------------------------------------- #
                # Dodanie paska w celu wyświetlenia liczby przejeżdzających pojazdów
                cv2.rectangle(frame, (0, 0), (width, 70), config.purpleColor, -1)
                cv2.putText(frame, text, (round(width / 2) - 300, 50), cv2.FONT_HERSHEY_DUPLEX, 2, config.blueColor, 2)
                cv2.line(frames[i - 1], (0, line_y), (width, line_y), config.lineColor, 3)

                # ------------------------------------------------------------------------- #
                # *Opcjonalnie* - wyświetlenie okienek po wykonaniu odpowiednich operacji na obrazie,
                #  wystarczy odkomentować poniższe dwie linie:
                # cv2.imshow("Closed-eroded", erodedFrames[i - 1])
                # cv2.imshow("thresh", threshFrames[i - 1])
                cv2.imshow("Monitoring_system", frames[i - 1])
                cv2.waitKey(wait_key)

        i += 1
    # ------------------------- KONIEC PĘTLI WHILE --------------------------------- #


# ------------------------------- G U I ------------------------------------- #
# Stworzenie okna użytkownika:
window = Tk(className="System wykrywania samochodów")
window.geometry("576x320")
window.resizable(False, False)
background_image = ImageTk.PhotoImage(Image.open("Autostrada-A2.png"))
background_label = Label(window, image=background_image)
background_label.place(x=0, y=0, relwidth=1, relheight=1)
buttonFont = font.Font(family="Helvetica", size=20, weight="normal")
movie_select_button = Button(bg="lemon chiffon", text="Wybierz film", command=capture_cars_from_source, font=buttonFont)
movie_select_button.config(height=3, width=14)
movie_select_button.place(relx=0.5, rely=0.5, anchor='center')

window.mainloop()

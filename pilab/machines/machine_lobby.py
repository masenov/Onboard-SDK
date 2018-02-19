class MachineLobby(object):
    def __init__(self):
        self.data = {"current_image":None}
    
    def change_img_id(self, img):
        self.data["current_image"] = img

    def update(self):
        pass

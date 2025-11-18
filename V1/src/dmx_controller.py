import ola
from ola.ClientWrapper import ClientWrapper

class DMXController:
    def __init__(self, universe=1):
        self.universe = universe
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()

    def send_rgb(self, r, g, b):
        data = bytearray([r, g, b] + [0]*(512-3))
        self.client.SendDmx(self.universe, data)

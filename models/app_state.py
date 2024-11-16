class AppState:
    def __init__(self):
        self.program_path = None
        self.emulator_name = None

    def update(self, config):
        self.program_path = config.get("path")
        self.emulator_name = config.get("emulator")

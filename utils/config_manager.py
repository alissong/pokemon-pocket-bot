import os


class ConfigManager:
    def __init__(self, filename="configs.txt"):
        self.filename = filename

    def load(self):
        config = {}
        if os.path.exists(self.filename):
            with open(self.filename) as f:
                for line in f:
                    if " = " in line:
                        key, val = line.strip().split(" = ")
                        config[key.strip()] = val.strip().strip('"')
        return config

    def save(self, key, value):
        config = self.load()
        config[key] = value
        with open(self.filename, "w") as f:
            for k, v in config.items():
                f.write(f'{k} = "{v}"\n')

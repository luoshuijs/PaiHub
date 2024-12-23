import toml


class TomlConfig(dict):
    def __init__(self, config_path: str):
        super().__init__()
        self._config_path = config_path
        self.read_toml_config()

    def read_toml_config(self):
        with open(self._config_path) as file:
            self.update(toml.load(file))

    def write_toml_config(self):
        with open(self._config_path, "w") as file:
            toml.dump(self, file)

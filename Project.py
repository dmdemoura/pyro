import configparser
import os
import sys

from GameType import GameType
from TimeElapsed import TimeElapsed


class Project:
    """Used to pass common data to single-file and project compilation"""
    USER_PATH_PART = os.path.join('Source', 'User').casefold()

    def __init__(self, game_type: GameType, input_path: str, output_path: str, namespace: str):
        self._ini = configparser.ConfigParser()
        self._ini.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'pyro.ini'))

        self.game_type = game_type
        self.game_path = self.get_game_path()
        self.input_path = input_path
        self.output_path = output_path
        self.namespace = namespace

    @property
    def is_fallout4(self):
        return self.game_type == GameType.Fallout4

    @property
    def is_skyrim_special_edition(self):
        return self.game_type == GameType.SkyrimSpecialEdition

    @property
    def is_skyrim_classic(self):
        return self.game_type == GameType.SkyrimClassic

    def _winreg_get_game_path(self) -> str:
        """Retrieve installed path of game using Windows Registry"""
        import winreg

        key_path, key_value = os.path.split(self._ini[self.game_type.name]['Registry'])

        try:
            registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
            reg_value, reg_type = winreg.QueryValueEx(registry_key, key_value)
            winreg.CloseKey(registry_key)
        except WindowsError:
            raise Exception('Game does not exist in Windows Registry. Run the game launcher once, then try again.')

        if not os.path.exists(reg_value):
            raise Exception('Directory does not exist:', reg_value)

        return reg_value

    @staticmethod
    def validate_script(script_path: str, time_elapsed: TimeElapsed):
        if not os.path.exists(script_path):
            print('[PYRO] Failed to write file: {0} (file does not exist)'.format(script_path))
        elif time_elapsed.start_time < os.stat(script_path).st_mtime < time_elapsed.end_time:
            print('[PYRO] Wrote file:', script_path)
        else:
            print('[PYRO] Failed to write file: {0} (not recently modified)'.format(script_path))

    def get_compiler_path(self) -> str:
        """Retrieve compiler path from pyro.ini"""
        return os.path.join(self.game_path, self._ini['Compiler']['Path'])

    def get_flags_path(self):
        """Retrieve flags path from pyro.ini"""
        return os.path.join(self.game_path, self._ini[self.game_type.name]['Flags'])

    def get_game_path(self) -> str:
        """Retrieve game path from either pyro.ini or Windows Registry"""
        game_path = self._ini['Shared']['GamePath']

        if len(game_path) > 0 and os.path.exists(game_path):
            return game_path

        if sys.platform == 'win32':
            return self._winreg_get_game_path()

        raise ValueError('Cannot retrieve game path from pyro.ini or Windows Registry')

    def get_scripts_base_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['BasePath'])

    def get_scripts_source_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['SourcePath'])

    def get_scripts_user_path(self) -> str:
        game_path = self.get_game_path()
        return os.path.join(game_path, self._ini['Shared']['UserPath'])

    def try_parse_relative_output_path(self) -> str:
        """Try to parse the user-defined relative project output path. If the path is not relative, return the unmodified path."""
        relative_base_path = os.path.dirname(self.input_path)

        if self.output_path == '..':
            project_output_path = [relative_base_path, os.pardir]

            if Project.USER_PATH_PART in os.path.join(*project_output_path).casefold():
                project_output_path = project_output_path + [os.pardir, os.pardir]

            if project_output_path is not None:
                return os.path.abspath(os.path.join(*project_output_path))

            return self.output_path

        if self.output_path == '.':
            return os.path.abspath(os.path.join(relative_base_path, os.curdir))

        if not os.path.isabs(self.output_path):
            raise ValueError('Cannot proceed with relative output path:', self.output_path)

        return self.output_path

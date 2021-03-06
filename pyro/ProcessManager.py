import logging
import os
import re
import subprocess
from decimal import Decimal

from pyro.Enums.ProcessState import ProcessState


class ProcessManager:
    log: logging.Logger = logging.getLogger('pyro')

    @staticmethod
    def _format_time(hours: Decimal, minutes: Decimal, seconds: Decimal) -> str:
        if hours.compare(0) == 1 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return f'{hours}h {minutes}m {seconds}s'
        if hours.compare(0) == 0 and minutes.compare(0) == 1 and seconds.compare(0) == 1:
            return f'{minutes}m {seconds}s'
        if hours.compare(0) == 0 and minutes.compare(0) == 0 and seconds.compare(0) == 1:
            return f'{seconds}s'
        return f'{hours}h {minutes}m {seconds}s'

    @staticmethod
    def run_command(command: str, cwd: str, env: dict) -> ProcessState:
        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True,
                                       shell=True,
                                       cwd=cwd,
                                       env=env)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        try:
            while process.poll() is None:
                line: str = process.stdout.readline().strip()
                if line:
                    ProcessManager.log.info(line)

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS

    @staticmethod
    def run_bsarch(command: str) -> ProcessState:
        """
        Creates bsarch process and logs output to console

        :param command: Command to execute, including absolute path to executable and its arguments
        :return: ProcessState (SUCCESS, FAILURE, INTERRUPTED, ERRORS)
        """
        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        exclusions = (
            '*',
            '[',
            'Archive Flags',
            'Bit',
            'BSArch',
            'Compressed',
            'Embed',
            'Files',
            'Format',
            'Packer',
            'Retain',
            'Startup',
            'Version',
            'XBox',
            'XMem'
        )

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if line.startswith(exclusions):
                    continue

                if line.startswith('Packing'):
                    package_path = line.split(':', 1)[1].strip()
                    ProcessManager.log.info(f'Packaging folder "{package_path}"...')
                    continue

                if line.startswith('Archive Name'):
                    archive_path = line.split(':', 1)[1].strip()
                    ProcessManager.log.info(f'Building "{archive_path}"...')
                    continue

                if line.startswith('Done'):
                    archive_time = line.split('in')[1].strip()[:-1]
                    hours, minutes, seconds = [round(Decimal(n), 3) for n in archive_time.split(':')]

                    timecode = ProcessManager._format_time(hours, minutes, seconds)

                    ProcessManager.log.info(f'Packaging time: {timecode}')
                    continue

                if line:
                    ProcessManager.log.info(line)

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS

    @staticmethod
    def run_compiler(command: str) -> ProcessState:
        """
        Creates compiler process and logs output to console

        :param command: Command to execute, including absolute path to executable and its arguments
        :return: ProcessState (SUCCESS, FAILURE, INTERRUPTED, ERRORS)
        """
        command_size = len(command)

        if command_size > 32768:
            ProcessManager.log.error(f'Cannot create process because command exceeds max length: {command_size}')
            return ProcessState.FAILURE

        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True)
        except WindowsError as e:
            ProcessManager.log.error(f'Cannot create process because: {e.strerror}')
            return ProcessState.FAILURE

        exclusions = (
            'Assembly',
            'Batch',
            'Compilation',
            'Copyright',
            'Failed',
            'No output',
            'Papyrus',
            'Starting'
        )

        line_error = re.compile(r'(.*)(\(\d+,\d+\)):\s+(.*)')

        try:
            while process.poll() is None:
                line = process.stdout.readline().strip()

                if not line or line.startswith(exclusions):
                    continue

                match = line_error.search(line)

                if match is not None:
                    path, location, message = match.groups()
                    head, tail = os.path.split(path)
                    ProcessManager.log.error(f'COMPILATION FAILED: '
                                             f'{os.path.basename(head)}\\{tail}{location}: {message}')
                    process.terminate()
                    return ProcessState.ERRORS

                if 'error(s)' not in line:
                    ProcessManager.log.info(line)

        except KeyboardInterrupt:
            try:
                process.terminate()
            except OSError:
                ProcessManager.log.error('Process interrupted by user.')
            return ProcessState.INTERRUPTED

        return ProcessState.SUCCESS

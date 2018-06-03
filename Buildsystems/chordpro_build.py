import sublime
import sublime_plugin

import subprocess
import threading
import os
from chopro.chopro2html import chopro2html

class ChordProBuild(sublime_plugin.WindowCommand):

    encoding = 'utf-8'
    killed = False
    proc = None
    panel = None
    panel_lock = threading.Lock()

    def is_enabled(self, to_html=False, to_pdf=False, to_lyrics=False, kill=False):
        # The Cancel build option should only be available
        # when the process is still running
        if kill:
            return self.proc is not None and self.proc.poll() is None
        return True

    def run(self, to_html=False, to_pdf=False, to_lyrics=False, kill=False):
        if kill:
            if self.proc:
                self.killed = True
                self.proc.terminate()
            return

        vars = self.window.extract_variables()
        working_dir = vars['file_path']

        # A lock is used to ensure only one thread is
        # touching the output panel at a time
        with self.panel_lock:
            # Creating the panel implicitly clears any previous contents
            self.panel = self.window.create_output_panel('exec')

            # Enable result navigation. The result_file_regex does
            # the primary matching, but result_line_regex is used
            # when build output includes some entries that only
            # contain line/column info beneath a previous line
            # listing the file info. The result_base_dir sets the
            # path to resolve relative file names against.
            settings = self.panel.settings()
            settings.set(
                'result_file_regex',
                r'^File "([^"]+)" line (\d+) col (\d+)'
            )
            settings.set(
                'result_line_regex',
                r'^\s+line (\d+) col (\d+)'
            )
            settings.set('result_base_dir', working_dir)

            self.window.run_command('show_panel', {'panel': 'output.exec'})

        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        args = [vars['file_name']]
        if to_lyrics:
            args.append('-l')

        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=working_dir
        )
        self.killed = False

        results = chopro2html.main(args)
        print('\n{0}\n'.format(results))

        threading.Thread(
            target=self.read_handle,
            args=(self.proc.stdout,)
        ).start()

    def read_handle(self, handle):
        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                # If exactly the requested number of bytes was
                # read, there may be more data, and the current
                # data may contain part of a multibyte char
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                # We pass out to a function to ensure the
                # timeout gets the value of out right now,
                # rather than a future (mutated) version
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''
            except (UnicodeDecodeError) as e:
                msg = 'Error decoding output using %s - %s'
                self.queue_write(msg  % (self.encoding, str(e)))
                break
            except (IOError):
                if self.killed:
                    msg = 'Cancelled'
                else:
                    msg = 'Finished'
                self.queue_write('\n[%s]' % msg)
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 1)

    def do_write(self, text):
        with self.panel_lock:
            self.panel.run_command('append', {'characters': text})

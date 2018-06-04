import sublime
import sublime_plugin

import subprocess
import threading
import os
from .commands.chopro import ChoPro
from .commands.fpdf import fpdf, html


class MakeFPDF(fpdf.FPDF, html.HTMLMixin):
    pass


class ChordProBuildCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return True

    def run(self, to_html=False, to_pdf=False, to_lyrics=False, kill=False):
        print('Run!')
        vars = self.window.extract_variables()
        file = vars['file']
        working_dir = vars['file_path']

        f = open(file, 'r')
        chopro_text = f.read()
        f.close()
        chopro = ChoPro(chopro_text)
        html = chopro.get_html(html_style='table')
        print(html)

        pdf = MakeFPDF()
        #First page
        pdf.add_page()
        pdf.write_html(html)
        pdf.output(os.path.join(working_dir, 'html.pdf'), 'F')
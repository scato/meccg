import os
import urllib.request


def load_html(url):
    basename = url.split('/')[-1]
    if basename == '':
        basename = 'index.html'
    filename = f"var/html/{basename}"
    if not os.path.exists(filename):
        with urllib.request.urlopen(url) as fp_in, open(filename, 'wb') as fp_out:
            fp_out.write(fp_in.read())

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin


from .misc import response_err, error, keyboard_inter
from .colors import colors
from . import config

class download():
    """
    Download Class.
    For all but the 
    download_cli() function
    a entry with all fields is required.
    If cli is False it wont print to stdout
    """
    def __init__(self, entry, cli=True) -> None:
        self.entry = entry
        self.headers = {"referer": self.entry.embed_url}
        self.cli = cli

    def get_ts_links(self):
        """ 
        Gets all ts links
        from a m3u8 playlist.
        M3u8 link must have gone trough
        videourl().quality() to work 
        properly.
        """
        r = requests.get(self.entry.stream_url, headers=self.headers)
        self.ts_link_names = [x for x in r.text.split('\n')]
        self.ts_link_names = [x for x in self.ts_link_names if not x.startswith('#')]
        self.ts_links = [urljoin(self.entry.stream_url, x.strip()) for x in self.ts_link_names]
        self.link_count = len(self.ts_links)
         
    def download_ts(self, ts_link, fname):
        r = self.session.get(ts_link, headers=self.headers)
        response_err(r, ts_link)
        file_path = self.temp_folder / fname
        print(f'{colors.CYAN}Downloading Parts: {colors.RED}({self.counter}/{self.link_count}) {colors.END}' ,end='\r')
        with open(file_path, 'wb') as file:
            for data in r.iter_content(chunk_size=1024):
                file.write(data)
        self.counter += 1 
        
    def multithread_dl(self):
        """
        Multithread download 
        function for ts links.
        - Creates show and temp folder
        - Starts ThreadPoolExecutor instance
          and downloads all ts links
        - Merges ts files 
        - Delets temp folder
        """
        self.get_ts_links()
        self.show_folder = config.download_folder_path / f'{self.entry.show_name}'
        self.temp_folder = self.show_folder / f'{self.entry.ep}_temp'
        config.download_folder_path.mkdir(exist_ok=True)
        self.show_folder.mkdir(exist_ok=True)
        self.temp_folder.mkdir(exist_ok=True) 
        self.counter = 0
        self.session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        if self.cli:
            print('-'*20)
            print(f'{colors.CYAN}Downloading: {colors.RED} {self.entry.show_name} EP: {self.entry.ep} {colors.END}')

        try:
            with ThreadPoolExecutor(self.link_count) as pool:
                pool.map(self.download_ts, self.ts_links, self.ts_link_names)
        except KeyboardInterrupt:
            shutil.rmtree(self.temp_folder)
            keyboard_inter()
            sys.exit()
        if self.cli:
            print(f'\n{colors.CYAN}Parts Downloaded')
        self.merge_files()
        if self.cli:
            print(f'\n{colors.CYAN}Parts Merged')
        shutil.rmtree(self.temp_folder)

    def merge_files(self):
        """ 
        Merge downloded ts files
        into one mp4.
        """
        out_file = self.show_folder / f'{self.entry.show_name}_{self.entry.ep}.mp4'
        try:
            with open(out_file, 'wb') as f:
                self.counter = 1
                for i in self.ts_link_names:
                    if self.cli:
                        print(f'{colors.CYAN}Merging Parts: {colors.RED} ({self.counter}/{self.link_count}) {colors.END}', end='\r')
                    try:
                        if i != '':
                            with open(self.temp_folder / i, 'rb') as t:
                                f.write(t.read())
                        else:
                            pass
                    except FileNotFoundError:
                            pass

                    self.counter += 1

        except PermissionError:
           error(f'could not create file due to permissions: {out_file}')
    
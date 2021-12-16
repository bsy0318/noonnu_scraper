import os
import sys
import time
import unicodedata
import requests
import json
import fontTools
from fontTools import ttLib

from rich import *
from rich.console import Console
console = Console()

console.log(ttLib.woff2)

file_list = os.listdir("WebFont")
for file in file_list:
    #font = ttLib.woff2.decompress(f"WebFont\\"+file,"font\\"+os.path.basename(file)+".otf")
    console.log(os.path.basename(file)+".otf Convert Complete.")
    
    
    
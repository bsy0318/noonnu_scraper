import os
import sys
import time
import unicodedata
import requests
import json
from fontTools import ttLib

from rich import *
from rich.console import Console
console = Console()

def fontlist_parse(limit_page):
    list_data=list()
    try:
        for i in range(1, limit_page):
            response = requests.get(f"https://noonnu.cc/font_page.json?page={i}&controller=fonts&action=index")
            list_data.append(json.dumps(response.json()))
            local_json = response.json()
            if  local_json["is_last_page"] == True:
                console.log("마지막 페이지 입니다.")
                break
            else:
                console.log(f"https://noonnu.cc/font_page.json?page={i}&controller=fonts&action=index 진행완료")
            #time.sleep(0.5)
    except Exception as e:
        console.log("[!] fontlist_parse에서 오류가 발생했습니다.")
        console.log(e)
    return list_data

def download_all(list_data,path):
    createFolder(path)
    for font_list in list_data:
        font_list_json = json.loads(font_list)
        for data in font_list_json["fonts"]:
            try:
                if data["cdn_server_html"].find("@import") != -1:
                    continue
                font_name = data["name"]
                font_downlink = data["cdn_server_html"].split("url('")[1].split("')")[0]
                font_format = data["cdn_server_html"].split("format('")[1].split("')")[0]
                download(font_downlink,f"{path}\\{font_name}.{font_format}")
                console.log(f"{font_name}.{font_format} Download Complete.")
            except Exception as e:
                console.log("[!] download_all에서 오류가 발생했습니다.")
                console.log(data["name"])
                console.log(e)
    return 0

def makeTTF(path_dir,save_path):
    createFolder(save_path)
    file_list = os.listdir(path_dir)
    for file in file_list:
        try:
            font = ttLib.woff2.decompress(f"{path_dir}\\"+file,f"{save_path}\\"+os.path.basename(file)+".otf")
            console.log(os.path.basename(file)+".otf Convert Complete.")
        except Exception as e:
            console.log("[!] makeTTF 에서 오류가 발생했습니다.")
            console.log(e)
    return 0

def download(url, file_name):
    with open(file_name, "wb") as file:   # open in binary mode
        response = requests.get(url)               # get request
        file.write(response.content)      # write to file
        
def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)

def main():
    page_depth = 500 #depth of the Font Page.
    list_data = fontlist_parse(page_depth)
    download_all(list_data,"WebFont")
    makeTTF("WebFont","font")
    return 0

if __name__ == "__main__":
	main()
    
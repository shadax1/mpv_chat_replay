import os
from datetime import datetime, timedelta
import re
import subprocess, json
os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]
import mpv #https://github.com/jaseg/python-mpv

def get_chat_lines(video_start_time, video_end_time, log_path, log_year):
    line_count = 0
    temp_line_month = 1
    temp_log_year = log_year #keep a trace of the first year logging started
    dict_year = {}
    dict_year[log_year] = 1
    lst_line = []
    regex = re.compile(r"<\w+>") #used to scan for lines containing <username>

    with open(log_path, mode="rt", encoding="utf-8") as fp:
        '''keeping all the log lines into a list because I have to do 2 loops
        and I don't think I can do 2 loops on fp.readlines() within the same
        with statement, so I prefer doing a single file access and store everything'''
        lst_line = fp.readlines()

    #1st loop to identify on which line each year starts in the log file
    for line in lst_line:
        line_count += 1
        if len(regex.findall(line)) != 0: #when we find a line with a chat message containing <username>
            line_month = datetime.strptime(line[:3], "%b").month
            if line_month >= temp_line_month:
                temp_line_month = line_month
            else:
                temp_log_year += 1
                dict_year[temp_log_year] = line_count
                temp_line_month = 1
    print(dict_year)
    line_count = 0
    temp_line_month = 1
    temp_log_year = log_year
    dict_chat = {}
    same_year = True
    december = False
    new_year = False
    #slice the list of chat lines to scan
    if video_start_time.year == video_end_time.year: #stream happened in the same year
        year = video_start_time.year
        try:
            lst_line = lst_line[dict_year[year]-1:dict_year[year+1]-1]
        except KeyError: #means the stream happened in the current year
            lst_line = lst_line[dict_year[year]-1:]
    else: #the stream is happening in the last day of december and continues into january the next year
        try:
            lst_line = lst_line[dict_year[video_start_time.year]-1:dict_year[video_end_time.year+1]-1]
        except KeyError: #means the stream happened in the current year
            lst_line = lst_line[dict_year[video_start_time.year]-1:]
        same_year = False

    #2nd loop to store all the relevant lines
    for line in lst_line:
        if len(regex.findall(line)) != 0: #when we find a line with a chat message containing <username>
            if same_year: #stream is happening in the same year
                line_date = datetime(
                    year=video_start_time.year,
                    month=datetime.strptime(line[:3], "%b").month, 
                    day=int(line[4:6]),
                    hour=int(line[7:9]),
                    minute=int(line[10:12]),
                    second=int(line[13:15]))
            else: #stream is happening just before new year's and goes into it
                if datetime.strptime(line[:3], "%b").month == 12: #once we get to december
                    line_date = datetime(
                        year=video_start_time.year,
                        month=datetime.strptime(line[:3], "%b").month, 
                        day=int(line[4:6]),
                        hour=int(line[7:9]),
                        minute=int(line[10:12]),
                        second=int(line[13:15]))
                    december = True #flag the fact that we are in december
                if december:
                    if datetime.strptime(line[:3], "%b").month == 1:
                        new_year = True
                if not new_year: #while new year doesn't happen
                    line_date = datetime(
                        year=video_start_time.year, #save the start year date
                        month=datetime.strptime(line[:3], "%b").month, 
                        day=int(line[4:6]),
                        hour=int(line[7:9]),
                        minute=int(line[10:12]),
                        second=int(line[13:15]))
                else: #when new year starts
                    line_date = datetime(
                        year=video_end_time.year, #save the new year date instead
                        month=datetime.strptime(line[:3], "%b").month, 
                        day=int(line[4:6]),
                        hour=int(line[7:9]),
                        minute=int(line[10:12]),
                        second=int(line[13:15]))

            if line_date >= video_start_time:
                if line_date > video_end_time:
                    break
                else:
                    #temp = line.split(f"{line_date.hour}:{line_date.minute}:{line_date.second}")
                    #dict_chat[line_date] = temp[-1].strip() #mapping -> timestamp:chat message
                    temp = line.split(" <")
                    msg = f"<{temp[-1].strip()}"
                    dict_chat[line_date] = msg #mapping -> timestamp:chat message
    return dict_chat

def get_video_duration(video_path):
    #this will return a bunch of metadata related to the video file
    result = subprocess.check_output(fr'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{video_path}"',shell=True).decode()
    fields = json.loads(result)['streams'][0]
    video_duration = fields['duration'] #only need the duration (stored as float in seconds)
    return video_duration

mpv_time_old = 0
def show_chat(mpv_time, dict_chat, video_start_time):
    global mpv_time_old

    mpv_time_date = video_start_time + timedelta(seconds=mpv_time)
    proper_minute = ""
    if mpv_time_old > mpv_time: #means the user went backwards in the video
        os.system('cls||clear')
        for item in dict_chat.items():
            #only display chat lines until the current mpv time has been reached
            if item[0] <= mpv_time_date:
                if item[0].minute <= 9:
                    proper_minute = f"0{item[0].minute}"
                    print(f"{item[0].hour}:{proper_minute} {item[1]}")
                else:
                    print(f"{item[0].hour}:{item[0].minute} {item[1]}")
    else:
        mpv_time_date_old = video_start_time + timedelta(seconds=mpv_time_old)
        for item in dict_chat.items():
            #only add chat lines that happened in between the old mpv time and the new one
            if item[0] >= mpv_time_date_old and item[0] < mpv_time_date:
                if item[0].minute <= 9:
                    proper_minute = f"0{item[0].minute}"
                    print(f"{item[0].hour}:{proper_minute} {item[1]}")
                else:
                    print(f"{item[0].hour}:{item[0].minute} {item[1]}")

    mpv_time_old = mpv_time

if __name__ == "__main__": #if ran as a script
    print("Enter the path to the video to play:")
    video_path = input()

    temp = video_path.split("-")
    year = int(temp[0][-4:])
    month = temp[1]
    day = temp[2][:2]
    hour = temp[2][3:]
    minute = temp[3]
    second = temp[-1][:2]

    video_start_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))

    #get the path to the chat log file
    print("Enter the path to the chat log:")
    log_path = input()

    #get the year for when chat logging started from the user
    print("Enter the year for when logging started:")
    log_year = int(input())

    video_duration = get_video_duration(video_path)
    video_duration = float(video_duration)
    video_end_time = video_start_time + timedelta(seconds=int(video_duration))
    print(f"[SCRIPT] Video starts {video_start_time}...")
    print(f"[SCRIPT] Video ends {video_end_time}...")
    print("[SCRIPT] Gathering chat lines from the log file...")
    dict_chat = get_chat_lines(video_start_time, video_end_time, log_path, log_year)
    if dict_chat: #if there are chat lines
        print("[SCRIPT] Starting the video")

        player = mpv.MPV(ytdl=True, input_default_bindings=True, input_vo_keyboard=True, osc=True)

        # Property access, these can be changed at runtime
        @player.property_observer('time-pos')
        def time_observer(_name, value):
            # Here, value is either None if nothing is playing or a float containing
            # fractional seconds since the beginning of the file.
            #print('Now playing at {:.2f}s'.format(value))
            mpv_time = int(value)
            show_chat(mpv_time, dict_chat, video_start_time)
        
        os.system('cls||clear')
        player.play(video_path)
        player.wait_for_playback()
        del player
    else:
        print("[SCRIPT] There is no chat for that video")

#get ffprobe build from https://github.com/BtbN/FFmpeg-Builds/releases
#mpv-1.dll can be found here https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-20210801-git-416668d.7z/download
#must add that to the script folder
import tkinter as tk
import speech_recognition as sr
import requests
import json
import csv
import pyaudio
import pygame
from PIL import Image, ImageTk
from threading import Thread
recognizer = sr.Recognizer()
pygame.init()
pygame.mixer.init()

KEYWORD = "やっほ"  

def monitor_keyword():
    with sr.Microphone() as source:
        update_status("Listening for keyword...", "blue")
        while running:
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = recognizer.recognize_google(audio, language='ja-JP')
                if KEYWORD in text:
                    start_voice_input()
            except sr.WaitTimeoutError:
                pass  # タイムアウトは無視
            except sr.UnknownValueError:
                pass  # 認識できない音声は無視
            except sr.RequestError as e:
                update_status(f"Error: {e}", "red")
                print("Error:", e)
        update_status("Stopped listening", "green")
               

def start_recording():
    global running
    running = True
    update_status("Recording started", "blue")
    Thread(target=monitor_keyword).start()

def stop_recording():
    global running
    running = False
    update_status("Recording stopped", "green")

def start_voice_input():
    play_beep()
    with sr.Microphone() as source:
        print("Please say something:")
        audio = recognizer.listen(source)

    try:
        update_status("Processing voice input...", "blue")
        text = recognizer.recognize_google(audio, language='ja-JP')
        play_end()
        aoi_anser = process_input_and_log(text)
        response_box.insert(tk.END, "あなたの質問: " + text + "\n" + "葵ちゃんからの解答:" + aoi_anser + "\n")
        update_status("Ready", "green")
    except sr.UnknownValueError:
        update_status("Could not understand audio", "red")
        response_box.insert(tk.END, "Could not understand audio\n")
    except sr.RequestError as e:
        update_status(f"Error: {e}", "red")
        response_box.insert(tk.END, "Error: {0}\n".format(e))
    pass

def send_to_chatgpt(text):
    api_key = load_api_key()
    aoi_set = load_aoi_setting()
    past_conversations = get_past_conversations()
    past_conversations.append({"role": "user", "content": aoi_set + text})
    headers = {
        "Authorization": f"Bearer {api_key}",
        'Content-type': 'application/json',
        'X-Slack-No-Retry': '1'
    }
    data = {
        "model": "gpt-4-1106-preview",
        "max_tokens": 1024,
        "temperature": 0.9, 
        "messages": past_conversations    
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None
    return response.json()

def log_to_csv(question, answer, filename="chat_history.csv"):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        answer = answer.replace('\n', ' ')
        writer.writerow([question, answer])

def process_input_and_log(text):
    response = send_to_chatgpt(text)
    if response and "choices" in response and response["choices"]:
        answer = response["choices"][0].get("message").get("content")
        log_to_csv(text, answer)

        # VOICEVOX APIを使用して応答を音声に変換
        audio_data = text_to_speech(answer)
        pya = pyaudio.PyAudio()
    
        stream = pya.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True)
        
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
        pya.terminate()

        return answer
    else:
        return "No response or error occurred"
def load_api_key(filename="api_key.txt"):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read().strip()

def load_aoi_setting(filename="aoi_setting.txt"):
    with open(filename, "r" , encoding="utf-8") as file:
        return file.read().strip()

def get_past_conversations(filename="chat_history.csv", max_conversations=4):
    conversations = []

    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = list(reader)
        rows.reverse()  # 最新の行を先頭にする

        for row in rows[:max_conversations]:
            user_message = {'role': 'user', 'content': row[0]}
            system_message = {'role': 'system', 'content': row[1]}

            conversations.append(user_message)
            if system_message['content']:
                conversations.append(system_message)

    conversations.reverse()  # 元の順序に戻す
    return conversations

def text_to_speech(text, speaker_id=8):
    host = "127.0.0.1"
    port = 50021
    text = text.replace('\n', ' ')
    params = (
        ('text', text),
        ('speaker', speaker_id),
    )
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    synthesis = requests.post(
        f'http://{host}:{port}/synthesis',
        headers = {"Content-Type": "application/json"},
        params = params,
        data = json.dumps(query.json())
    )
    audio_response = synthesis.content
    return audio_response

def update_status(message, color="black"):
    """ ステータスメッセージを更新する関数 """
    status_label.config(text=message, fg=color)

def play_beep():
    beep_sound = pygame.mixer.Sound('beep.mp3')
    beep_sound.play()

def play_end():
    beep_sound = pygame.mixer.Sound('end.mp3')
    beep_sound.play()

# ウィンドウの作成
window = tk.Tk()
window.title("葵ちゃん Interface")
window.geometry("800x500")  # ウィンドウの幅と高さを設定

# 画像の読み込みとサイズ調整
image = Image.open("character_image.png")
image = image.resize((130, 300), Image.Resampling.LANCZOS)
photo = ImageTk.PhotoImage(image)

# メインフレームの作成
main_frame = tk.Frame(window)
main_frame.pack(expand=True, fill="both")

# 左側のフレーム（画像表示用）
left_frame = tk.Frame(main_frame, width=200)
left_frame.grid(row=0, column=0, sticky="ns")
left_frame.grid_propagate(False)

# 画像ラベルの作成と配置
image_label = tk.Label(left_frame, image=photo)
image_label.pack(side="top", fill="both", expand=True)

# 中央のフレーム（ボタンとテキストボックス用）
center_frame = tk.Frame(main_frame, width=600)
center_frame.grid(row=0, column=1, sticky="nsew")

# ボタン用のフレーム
button_frame = tk.Frame(center_frame)
button_frame.pack(side="top", fill="x", pady=10)

# ボタンの追加
start_voice_input_button = tk.Button(button_frame, text="Start Voice Input", command=start_voice_input)
start_voice_input_button.pack(side="left", padx=10)

start_recording_button = tk.Button(button_frame, text="Start Recording", command=start_recording)
start_recording_button.pack(side="left", padx=10)

stop_recording_button = tk.Button(button_frame, text="Stop Recording", command=stop_recording)
stop_recording_button.pack(side="left", padx=10)

# テキストボックスの追加
response_box = tk.Text(center_frame, height=15, width=50)
response_box.pack(padx=10, pady=10, fill="both", expand=True)

# ステータス表示用のフレーム
status_frame = tk.Frame(center_frame)
status_frame.pack(side="bottom", fill="x")

# ステータス表示用のラベルを追加
status_label = tk.Label(status_frame, text="Ready", fg="green")
status_label.pack(side="left", padx=10)

# 中央フレームのグリッドウェイト設定
center_frame.grid_rowconfigure(0, weight=1)
center_frame.grid_columnconfigure(1, weight=1)

# メインフレームのグリッドウェイト設定
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=1)

# ウィンドウの実行
window.mainloop()